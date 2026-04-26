import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from autodownloader.database import create_job, get_job, init_db, update_job_status
from autodownloader.logger import setup_logging
from autodownloader.processor import cleanup_job, cleanup_old_jobs, process_job

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)


async def _periodic_cleanup_task(stop_event: asyncio.Event, interval: int = 3600) -> None:
    try:
        while not stop_event.is_set():
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass
            else:
                break
            if not stop_event.is_set():
                try:
                    await cleanup_old_jobs()
                except Exception:
                    logger.exception("Periodic cleanup task encountered an error")
    except asyncio.CancelledError:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Application starting up...")
    await init_db()
    await cleanup_old_jobs()
    # Start background cleanup loop
    stop_event = asyncio.Event()
    cleanup_task = asyncio.create_task(_periodic_cleanup_task(stop_event))
    try:
        yield
    finally:
        stop_event.set()
        try:
            await asyncio.wait_for(cleanup_task, timeout=5)
        except asyncio.TimeoutError:
            logger.warning("Cleanup task did not finish within 5s, cancelling")
            cleanup_task.cancel()
        logger.info("Application shutting down...")
        logging.shutdown()


app = FastAPI(title="AutoDownloader", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, job_id: str | None = None):
    return templates.TemplateResponse(request, "index.html", {"job_id": job_id})


@app.post("/submit")
async def submit(
    url: str = Form(""),
    video_file: UploadFile | None = File(None),
    apply_ffmpeg: bool = Form(True),
    resolution: str = Form("1920x1080"),
    fps: str = Form("30"),
    codec: str = Form("libx265"),
    crf: int = Form(28),
    preset: str = Form("medium"),
    audio: str = Form("copy"),
):
    has_url = bool(url.strip())
    has_file = video_file is not None

    if has_url and has_file:
        raise HTTPException(status_code=400, detail="Provide either a URL or a file, not both.")
    if not has_url and not has_file:
        raise HTTPException(status_code=400, detail="Provide either a URL or a file.")

    job_id = str(uuid.uuid4())
    params = {
        "resolution": resolution,
        "fps": fps,
        "codec": codec,
        "crf": crf,
        "preset": preset,
        "audio": audio,
        "source_type": "url" if has_url else "upload",
        "apply_ffmpeg": apply_ffmpeg,
    }

    logger.info("Received submission job_id=%s url=%s has_file=%s params=%s", job_id, url, has_file, params)

    if has_file:
        # Save the uploaded file immediately so the processor can find it
        download_dir = Path("downloads") / job_id
        download_dir.mkdir(parents=True, exist_ok=True)
        safe_name = Path(video_file.filename).name
        file_path = download_dir / safe_name
        content = await video_file.read()
        file_path.write_bytes(content)
        logger.info("Job %s: Saved uploaded file to %s", job_id, file_path)

        await create_job(job_id, "", params)
        await update_job_status(job_id, "queued", original_filename=safe_name)
    else:
        await create_job(job_id, url, params)

    asyncio.create_task(process_job(job_id))
    return {"job_id": job_id}


@app.get("/status/{job_id}")
async def status(job_id: str):
    job = await get_job(job_id)
    if not job:
        logger.warning("Status requested for unknown job %s", job_id)
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job["id"],
        "status": job["status"],
        "message": job["message"],
        "created_at": job["created_at"],
        "updated_at": job["updated_at"],
        "original_filename": job["original_filename"],
        "final_filename": job["final_filename"],
    }


@app.get("/download/{job_id}")
async def download(job_id: str):
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "ready":
        raise HTTPException(
            status_code=400, detail=f"Job is not ready (status: {job['status']})"
        )

    download_dir = Path(job["download_dir"])
    final_name = job["final_filename"]
    if not final_name:
        raise HTTPException(status_code=500, detail="Final filename missing")

    file_path = download_dir / final_name
    if not file_path.exists():
        logger.error("Job %s: File missing on disk: %s", job_id, file_path)
        raise HTTPException(status_code=404, detail="File not found on disk")

    safe_name = "".join(c for c in final_name if c.isalnum() or c in "._- ").strip()
    if not safe_name:
        safe_name = "download.mp4"

    logger.info("Job %s: Serving download %s", job_id, file_path)
    return FileResponse(path=file_path, media_type="video/mp4", filename=safe_name)


@app.post("/delete/{job_id}")
async def delete_job_endpoint(job_id: str):
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await cleanup_job(job_id, delay_seconds=0)
    return {"detail": "Job deleted"}


def main() -> None:
    import uvicorn

    uvicorn.run("autodownloader.main:app", host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()
