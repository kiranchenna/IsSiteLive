from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.db import get_db

router = APIRouter(tags=["runs"])


@router.get("/api/sites/{site_id}/runs", response_model=list[schemas.CheckRunOut])
def list_runs(site_id: int, limit: int = 50, db: Session = Depends(get_db)):
    return (
        db.query(models.CheckRun)
        .filter(models.CheckRun.site_id == site_id)
        .order_by(models.CheckRun.started_at.desc())
        .limit(limit)
        .all()
    )


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


@router.get("/api/dashboard/status", response_model=list[schemas.SiteStatusOut])
def dashboard_status(db: Session = Depends(get_db)):
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
                }
            )
        result.append(
            schemas.SiteStatusOut(
                site_id=site.id,
                site_name=site.name,
                is_active=site.is_active,
                accounts=accounts_out,
            )
        )
    return result
