import asyncio
import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

RETENTION_SECONDS = int(os.getenv("RETENTION_SECONDS", "86400"))

from autodownloader.database import get_job, get_ready_jobs, update_job_status

logger = logging.getLogger(__name__)


async def _stream_logs(prefix: str, stream, job_id: str) -> None:
    if not stream:
        return
    while True:
        try:
            line = await stream.readline()
        except (ValueError, asyncio.LimitOverrunError):
            # Line exceeds stream buffer limit; skip the chunk so the job survives.
            logger.warning("Job %s: %s line too long, skipping chunk", job_id, prefix)
            continue
        if not line:
            break
        text = line.decode("utf-8", errors="replace").rstrip()
        if text:
            logger.debug("%s Job %s: %s", prefix, job_id, text)


async def run_yt_dlp(job_id: str, url: str, download_dir: Path) -> Path:
    download_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(download_dir / "%(title)s.%(ext)s")

    logger.info("Job %s: Starting yt-dlp download for %s", job_id, url)
    await update_job_status(job_id, "downloading", message="Starting download...")

    def _download() -> int:
        import yt_dlp

        ydl_opts = {
            "outtmpl": output_template,
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.download([url])

    error_code = await asyncio.to_thread(_download)

    if error_code != 0:
        logger.error("Job %s: yt-dlp failed with error code %d", job_id, error_code)
        raise RuntimeError("yt-dlp download failed")

    files = [f for f in download_dir.iterdir() if f.suffix not in (".part", ".ytdl")]
    if not files:
        raise RuntimeError("yt-dlp completed but no file was found")

    downloaded_file = files[0]
    logger.info("Job %s: Downloaded file %s", job_id, downloaded_file.name)
    return downloaded_file


def build_ffmpeg_command(input_path: Path, output_path: Path, params: dict) -> list[str]:
    resolution = params.get("resolution", "1920x1080")
    fps = params.get("fps", "30")
    codec = params.get("codec", "libx265")
    crf = str(params.get("crf", 28))
    preset = params.get("preset", "medium")
    audio = params.get("audio", "copy")

    vf_parts = []
    if resolution and resolution.lower() != "original":
        vf_parts.append(f"scale={resolution.replace('x', ':')}")
    if fps and fps.lower() != "original":
        vf_parts.append(f"fps={fps}")

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
    ]

    if vf_parts:
        cmd.extend(["-vf", ",".join(vf_parts)])

    cmd.extend(
        [
            "-c:v",
            codec,
            "-crf",
            crf,
            "-preset",
            preset,
            "-c:a",
            audio,
            str(output_path),
        ]
    )

    return cmd


def build_output_name(original_name: str, params: dict) -> str:
    p = Path(original_name)
    stem = p.stem
    suffix = ".mp4"
    codec = params.get("codec", "libx265").replace("lib", "")

    res = params.get("resolution", "original")
    fps = params.get("fps", "original")

    parts = [codec]
    if res.lower() != "original":
        parts.append(res.split("x")[1] + "p")
    if fps.lower() != "original":
        parts.append(fps)

    tag = "_".join(parts)
    return f"{stem}_{tag}{suffix}"


async def run_ffmpeg(job_id: str, input_path: Path, output_path: Path, params: dict) -> None:
    cmd = build_ffmpeg_command(input_path, output_path, params)
    logger.info("Job %s: Starting ffmpeg: %s", job_id, " ".join(cmd))
    await update_job_status(job_id, "processing", message="Starting ffmpeg processing...")

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        limit=2**20,
    )

    await asyncio.gather(
        _stream_logs("[ffmpeg stdout]", process.stdout, job_id),
        _stream_logs("[ffmpeg stderr]", process.stderr, job_id),
    )

    returncode = await process.wait()

    if returncode != 0:
        logger.error("Job %s: ffmpeg failed with exit code %d", job_id, returncode)
        raise RuntimeError("ffmpeg processing failed")

    logger.info("Job %s: ffmpeg finished -> %s", job_id, output_path.name)


async def process_job(job_id: str) -> None:
    logger.info("Job %s: Processor task started", job_id)
    job = await get_job(job_id)
    if not job:
        logger.error("Job %s: Not found in database", job_id)
        return

    try:
        params = json.loads(job["params_json"])
        download_dir = Path(job["download_dir"])
        source_type = params.get("source_type", "url")
        apply_ffmpeg = params.get("apply_ffmpeg", True)

        if source_type == "url":
            url = job["url"]
            downloaded_file = await run_yt_dlp(job_id, url, download_dir)
            await update_job_status(
                job_id,
                "downloading",
                message="Download complete",
                original_filename=downloaded_file.name,
            )

            if apply_ffmpeg:
                output_path = download_dir / build_output_name(downloaded_file.name, params)
                await run_ffmpeg(job_id, downloaded_file, output_path, params)
                await update_job_status(
                    job_id,
                    "ready",
                    message="Processing complete",
                    final_filename=output_path.name,
                )
                logger.info("Job %s: Ready for download", job_id)
            else:
                # Skip ffmpeg; the downloaded file is the final output
                await update_job_status(
                    job_id,
                    "ready",
                    message="Download complete (ffmpeg skipped)",
                    final_filename=downloaded_file.name,
                )
                logger.info("Job %s: Ready for download (ffmpeg skipped)", job_id)

        elif source_type == "upload":
            original_name = job.get("original_filename")
            if not original_name:
                raise RuntimeError("Uploaded file original name is missing")

            uploaded_file = download_dir / original_name
            if not uploaded_file.exists():
                raise RuntimeError(f"Uploaded file not found on disk: {uploaded_file}")

            await update_job_status(
                job_id,
                "processing",
                message="Starting processing for uploaded file...",
            )

            output_path = download_dir / build_output_name(original_name, params)
            await run_ffmpeg(job_id, uploaded_file, output_path, params)

            await update_job_status(
                job_id,
                "ready",
                message="Processing complete",
                final_filename=output_path.name,
            )
            logger.info("Job %s: Ready for download", job_id)
        else:
            raise RuntimeError(f"Unknown source_type: {source_type}")

        asyncio.create_task(cleanup_job(job_id, delay_seconds=RETENTION_SECONDS))
    except Exception:
        logger.exception("Job %s: Unhandled exception during processing", job_id)
        await update_job_status(job_id, "error", message="Processing failed (see logs)")


async def cleanup_job(job_id: str, delay_seconds: int) -> None:
    logger.info("Job %s: Cleanup scheduled in %d seconds", job_id, delay_seconds)
    await asyncio.sleep(delay_seconds)

    job = await get_job(job_id)
    if not job:
        logger.warning("Job %s: No DB record found during cleanup", job_id)
        return

    download_dir = Path(job["download_dir"]) if job["download_dir"] else None
    if download_dir and download_dir.exists():
        try:
            shutil.rmtree(download_dir)
            logger.info("Job %s: Deleted download directory %s", job_id, download_dir)
        except Exception as exc:
            logger.error("Job %s: Failed to delete directory (may be in use): %s", job_id, exc)

    if job["status"] != "expired":
        await update_job_status(
            job_id,
            "expired",
            message="File expired and was deleted after 24 hours.",
        )
        logger.info("Job %s: Status set to expired", job_id)


async def cleanup_old_jobs() -> None:
    logger.info("Running cleanup for old jobs...")
    jobs = await get_ready_jobs()
    now = datetime.now(timezone.utc)

    for job in jobs:
        updated_at = job.get("updated_at")
        if not updated_at:
            continue
        try:
            dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        except ValueError:
            try:
                dt = datetime.strptime(updated_at, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        age = (now - dt).total_seconds()
        if age > RETENTION_SECONDS:
            logger.info("Job %s: Expired on startup (age %.0f s)", job["id"], age)
            await cleanup_job(job["id"], delay_seconds=0)

    # Retry deletion for expired jobs whose directories may have been locked earlier
    downloads_dir = Path("downloads")
    if not downloads_dir.exists():
        return
    for subdir in downloads_dir.iterdir():
        if not subdir.is_dir():
            continue
        job = await get_job(subdir.name)
        if job and job["status"] == "expired":
            try:
                shutil.rmtree(subdir)
                logger.info("Cleaned up leftover directory for expired job %s", subdir.name)
            except Exception as exc:
                logger.warning(
                    "Could not delete leftover directory for job %s: %s", subdir.name, exc
                )
