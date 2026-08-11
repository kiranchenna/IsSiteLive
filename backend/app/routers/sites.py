import asyncio
from datetime import datetime, time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import models, reports, schemas
from app.db import get_db

router = APIRouter(prefix="/api/sites", tags=["sites"])


def _with_next_run(site: models.Site) -> models.Site:
    from app.scheduler import get_next_run_time

    site.next_run_at = get_next_run_time(site.id)  # transient attribute, not a DB column
    return site


@router.get("", response_model=list[schemas.SiteOut])
def list_sites(db: Session = Depends(get_db)):
    sites = db.query(models.Site).order_by(models.Site.name).all()
    return [_with_next_run(s) for s in sites]


@router.post("", response_model=schemas.SiteOut, status_code=201)
def create_site(payload: schemas.SiteCreate, db: Session = Depends(get_db)):
    site = models.Site(**payload.model_dump())
    db.add(site)
    db.commit()
    db.refresh(site)

    from app.scheduler import schedule_site

    schedule_site(site.id)
    return _with_next_run(site)


@router.get("/{site_id}", response_model=schemas.SiteOut)
def get_site(site_id: int, db: Session = Depends(get_db)):
    site = db.get(models.Site, site_id)
    if not site:
        raise HTTPException(404, "Site not found")
    return _with_next_run(site)


@router.put("/{site_id}", response_model=schemas.SiteOut)
def update_site(site_id: int, payload: schemas.SiteUpdate, db: Session = Depends(get_db)):
    site = db.get(models.Site, site_id)
    if not site:
        raise HTTPException(404, "Site not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(site, field, value)
    db.commit()
    db.refresh(site)

    from app.scheduler import schedule_site, unschedule_site

    if site.is_active:
        schedule_site(site.id)
    else:
        unschedule_site(site.id)
    return _with_next_run(site)


@router.delete("/{site_id}", status_code=204)
def delete_site(site_id: int, db: Session = Depends(get_db)):
    site = db.get(models.Site, site_id)
    if not site:
        raise HTTPException(404, "Site not found")
    db.delete(site)
    db.commit()

    from app.scheduler import unschedule_site

    unschedule_site(site_id)


@router.put("/{site_id}/flow", response_model=schemas.FlowOut)
def upsert_flow(site_id: int, payload: schemas.FlowUpsert, db: Session = Depends(get_db)):
    site = db.get(models.Site, site_id)
    if not site:
        raise HTTPException(404, "Site not found")
    flow = db.query(models.Flow).filter(models.Flow.site_id == site_id).first()
    if flow:
        flow.steps_json = payload.steps_json
        flow.watch_patterns_json = payload.watch_patterns_json
    else:
        flow = models.Flow(site_id=site_id, **payload.model_dump())
        db.add(flow)
    db.commit()
    db.refresh(flow)
    return flow


@router.get("/{site_id}/flow", response_model=schemas.FlowOut)
def get_flow(site_id: int, db: Session = Depends(get_db)):
    flow = db.query(models.Flow).filter(models.Flow.site_id == site_id).first()
    if not flow:
        raise HTTPException(404, "Flow not configured for this site")
    return flow


@router.get("/{site_id}/alert-channels", response_model=list[int])
def get_site_alert_channels(site_id: int, db: Session = Depends(get_db)):
    site = db.get(models.Site, site_id)
    if not site:
        raise HTTPException(404, "Site not found")
    links = db.query(models.SiteAlertChannel).filter(models.SiteAlertChannel.site_id == site_id).all()
    return [link.alert_channel_id for link in links]


@router.put("/{site_id}/alert-channels", status_code=204)
def set_site_alert_channels(site_id: int, payload: schemas.SiteAlertChannelsUpdate, db: Session = Depends(get_db)):
    site = db.get(models.Site, site_id)
    if not site:
        raise HTTPException(404, "Site not found")
    db.query(models.SiteAlertChannel).filter(models.SiteAlertChannel.site_id == site_id).delete()
    for channel_id in payload.alert_channel_ids:
        db.add(models.SiteAlertChannel(site_id=site_id, alert_channel_id=channel_id))
    db.commit()


@router.post("/{site_id}/run-now", status_code=202)
async def run_now(site_id: int, db: Session = Depends(get_db)):
    site = db.get(models.Site, site_id)
    if not site:
        raise HTTPException(404, "Site not found")

    from app.scheduler import run_site_check

    # Fire-and-forget: a check can legitimately take minutes (see DEFAULT_STEP_TIMEOUT_MS),
    # so this must not block the request -- the client reads progress back from run history
    # (status="running" until it resolves) instead of waiting on this call to return.
    asyncio.create_task(run_site_check(site_id, force=True))
    return {"status": "triggered"}


@router.get("/{site_id}/report.xlsx")
def download_report(
    site_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    site = db.get(models.Site, site_id)
    if not site:
        raise HTTPException(404, "Site not found")

    status_filter = None
    if status is not None:
        if status not in ("success", "fail"):
            raise HTTPException(422, f"Invalid status filter: {status!r} (expected 'success' or 'fail')")
        status_filter = models.RunStatus(status)

    def _parse_date(value: str, param: str, end_of_day: bool) -> datetime:
        try:
            date_only = datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(422, f"Invalid {param}: {value!r} (expected YYYY-MM-DD)") from None
        return datetime.combine(date_only, time.max if end_of_day else time.min)

    start_dt = _parse_date(start_date, "start_date", end_of_day=False) if start_date else None
    end_dt = _parse_date(end_date, "end_date", end_of_day=True) if end_date else None

    buffer = reports.build_site_report(db, site, start_date=start_dt, end_date=end_dt, status_filter=status_filter)
    filename = reports.report_filename(site, status_filter=status_filter)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
