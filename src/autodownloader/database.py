import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import aiosqlite

logger = logging.getLogger(__name__)

DB_PATH = Path("data/jobs.db")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


async def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                download_dir TEXT,
                original_filename TEXT,
                final_filename TEXT,
                params_json TEXT
            )
            """
        )
        await db.commit()
    logger.info("Database initialized at %s", DB_PATH.resolve())


async def create_job(job_id: str, url: str, params: dict) -> None:
    params_json = json.dumps(params)
    download_dir = str(Path("downloads") / job_id)
    now = _now_iso()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO jobs (id, url, status, created_at, updated_at, download_dir, params_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (job_id, url, "queued", now, now, download_dir, params_json),
        )
        await db.commit()
    logger.info("Created job %s for URL %s", job_id, url)


async def update_job_status(
    job_id: str,
    status: str,
    message: Optional[str] = None,
    original_filename: Optional[str] = None,
    final_filename: Optional[str] = None,
) -> None:
    now = _now_iso()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE jobs SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, job_id),
        )
        if message is not None:
            await db.execute(
                "UPDATE jobs SET message = ? WHERE id = ?",
                (message, job_id),
            )
        if original_filename is not None:
            await db.execute(
                "UPDATE jobs SET original_filename = ? WHERE id = ?",
                (original_filename, job_id),
            )
        if final_filename is not None:
            await db.execute(
                "UPDATE jobs SET final_filename = ? WHERE id = ?",
                (final_filename, job_id),
            )
        await db.commit()
    logger.info("Updated job %s status to %s", job_id, status)


async def get_job(job_id: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None


async def get_ready_jobs() -> List[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM jobs WHERE status = 'ready'") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
