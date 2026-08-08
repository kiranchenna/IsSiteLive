import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.db import SessionLocal

logger = logging.getLogger("issitelive.retention")

SWEEP_INTERVAL_SECONDS = 24 * 60 * 60  # once a day is plenty for a days-granularity policy
_sweeper_task: Optional[asyncio.Task] = None


def sweep_expired_screenshots(db: Session, days: Optional[int] = None) -> dict:
    """Deletes screenshot files (and clears their DB reference) for any run older than
    `days` -- falls back to settings.screenshot_retention_days when not given, so a caller
    that doesn't mention a number of days still gets the configured default applied.

    Run history itself (status, duration, step pass/fail) is kept; only the disk-heavy
    images are pruned, since that's what actually grows unbounded over time.
    """
    retention_days = days if days is not None else settings.screenshot_retention_days
    cutoff = datetime.utcnow() - timedelta(days=retention_days)

    expired = (
        db.query(models.StepResult)
        .join(models.CheckRun, models.StepResult.check_run_id == models.CheckRun.id)
        .filter(models.CheckRun.started_at < cutoff, models.StepResult.screenshot_path.isnot(None))
        .all()
    )

    deleted_files = 0
    for step in expired:
        filename = os.path.basename(step.screenshot_path)
        disk_path = os.path.join(settings.screenshots_dir, filename)
        try:
            os.remove(disk_path)
            deleted_files += 1
        except FileNotFoundError:
            pass
        except OSError:
            logger.exception("Failed to delete screenshot %s", disk_path)
        step.screenshot_path = None

    db.commit()
    return {"retention_days": retention_days, "cleared_step_results": len(expired), "deleted_files": deleted_files}


async def _sweep_loop() -> None:
    while True:
        try:
            db = SessionLocal()
            try:
                result = await asyncio.to_thread(sweep_expired_screenshots, db)
            finally:
                db.close()
            if result["cleared_step_results"]:
                logger.info("Screenshot retention sweep: %s", result)
        except Exception:  # noqa: BLE001 - one failed sweep must not kill the daily loop
            logger.exception("Screenshot retention sweep failed")
        await asyncio.sleep(SWEEP_INTERVAL_SECONDS)


def start_sweeper() -> None:
    global _sweeper_task
    _sweeper_task = asyncio.create_task(_sweep_loop())


def stop_sweeper() -> None:
    if _sweeper_task:
        _sweeper_task.cancel()
