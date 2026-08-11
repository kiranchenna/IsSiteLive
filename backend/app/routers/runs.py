from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app import models, retention, schemas
from app.db import get_db

router = APIRouter(tags=["runs"])


@router.get("/api/sites/{site_id}/runs", response_model=schemas.PaginatedRunsOut)
def list_runs(
    site_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(models.CheckRun).filter(models.CheckRun.site_id == site_id).order_by(models.CheckRun.started_at.desc())
    total = query.count()
    items = query.offset(offset).limit(limit).all()
    return schemas.PaginatedRunsOut(items=items, total=total, limit=limit, offset=offset)


@router.get("/api/runs/{run_id}", response_model=schemas.CheckRunDetailOut)
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = (
        db.query(models.CheckRun)
        .options(joinedload(models.CheckRun.step_results))
        .filter(models.CheckRun.id == run_id)
        .first()
    )
    if not run:
        raise HTTPException(404, "Run not found")
    return run


@router.post("/api/screenshots/cleanup")
def cleanup_screenshots(days: Optional[int] = None, db: Session = Depends(get_db)):
    """Deletes screenshot files older than `days` (defaults to SCREENSHOT_RETENTION_DAYS
    when not given). Runs automatically once a day; this exists to trigger it on demand."""
    return retention.sweep_expired_screenshots(db, days)


@router.get("/api/dashboard/status", response_model=list[schemas.SiteStatusOut])
def dashboard_status(db: Session = Depends(get_db)):
    from app.scheduler import get_next_run_time

    sites = db.query(models.Site).order_by(models.Site.name).all()
    result = []
    for site in sites:
        accounts_out = []
        for account in site.accounts:
            last_run = (
                db.query(models.CheckRun)
                .filter(models.CheckRun.account_id == account.id)
                .order_by(models.CheckRun.started_at.desc())
                .first()
            )
            accounts_out.append(
                {
                    "account_id": account.id,
                    "label": account.label,
                    "last_status": last_run.status.value if last_run else "unknown",
                    "last_run_at": last_run.started_at.isoformat() if last_run else None,
                    "error_summary": last_run.error_summary if last_run else None,
                }
            )
        result.append(
            schemas.SiteStatusOut(
                site_id=site.id,
                site_name=site.name,
                is_active=site.is_active,
                next_run_at=get_next_run_time(site.id),
                accounts=accounts_out,
            )
        )
    return result
