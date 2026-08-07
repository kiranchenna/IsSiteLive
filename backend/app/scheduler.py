import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app import models
from app.alerts.dispatcher import dispatch_alert_for_run
from app.checker.runner import run_check
from app.config import settings
from app.db import SessionLocal

logger = logging.getLogger("issitelive.scheduler")

scheduler = AsyncIOScheduler()
_semaphore = asyncio.Semaphore(settings.default_check_concurrency)


def _job_id(site_id: int) -> str:
    return f"site-check-{site_id}"


async def run_site_check(site_id: int) -> None:
    """Runs the flow for every active account of a site, with a global concurrency cap."""
    db = SessionLocal()
    try:
        site = db.get(models.Site, site_id)
        if not site or not site.is_active:
            return
        flow = db.query(models.Flow).filter(models.Flow.site_id == site_id).first()
        if not flow:
            logger.warning("Site %s has no flow configured, skipping check", site_id)
            return
        accounts = db.query(models.Account).filter(models.Account.site_id == site_id, models.Account.is_active.is_(True)).all()
    finally:
        db.close()

    await asyncio.gather(*(_run_one_account(site_id, account.id) for account in accounts))


async def _run_one_account(site_id: int, account_id: int) -> None:
    async with _semaphore:
        db = SessionLocal()
        try:
            site = db.get(models.Site, site_id)
            account = db.get(models.Account, account_id)
            flow = db.query(models.Flow).filter(models.Flow.site_id == site_id).first()
            if not site or not account or not flow:
                return
            try:
                check_run = await run_check(db, site, account, flow)
            except Exception:  # noqa: BLE001 - a crashed browser run must not kill the scheduler loop
                logger.exception("Check run crashed for site=%s account=%s", site_id, account_id)
                return
            dispatch_alert_for_run(db, check_run)
        finally:
            db.close()


def schedule_site(site_id: int) -> None:
    db = SessionLocal()
    try:
        site = db.get(models.Site, site_id)
        if not site or not site.is_active:
            unschedule_site(site_id)
            return
        interval = site.check_interval_seconds
    finally:
        db.close()

    scheduler.add_job(
        run_site_check,
        trigger=IntervalTrigger(seconds=interval),
        args=[site_id],
        id=_job_id(site_id),
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )


def unschedule_site(site_id: int) -> None:
    job_id = _job_id(site_id)
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)


def load_all_sites() -> None:
    db = SessionLocal()
    try:
        site_ids = [s.id for s in db.query(models.Site).filter(models.Site.is_active.is_(True)).all()]
    finally:
        db.close()
    for site_id in site_ids:
        schedule_site(site_id)


def start() -> None:
    load_all_sites()
    scheduler.start()


def shutdown() -> None:
    scheduler.shutdown(wait=False)
