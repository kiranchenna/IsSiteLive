import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import settings

os.makedirs(os.path.dirname(settings.database_url.replace("sqlite:///", "")) or ".", exist_ok=True)

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app import models  # noqa: F401 ensure models are registered

    Base.metadata.create_all(bind=engine)


def reconcile_interrupted_runs(db: Optional[Session] = None) -> int:
    """A CheckRun can be left at status=running forever if the process dies mid-check
    (crash, kill, restart) -- there's nothing left to ever resolve it. Run once at startup
    so a stale "running" row never shows as in-progress indefinitely after a restart.
    Returns the number of runs reconciled."""
    from datetime import datetime

    from app import models

    owns_session = db is None
    db = db or SessionLocal()
    try:
        stuck = db.query(models.CheckRun).filter(models.CheckRun.status == models.RunStatus.running).all()
        for run in stuck:
            run.status = models.RunStatus.fail
            run.error_summary = "Interrupted: server restarted before this check finished"
            run.finished_at = datetime.utcnow()
        if stuck:
            db.commit()
        return len(stuck)
    finally:
        if owns_session:
            db.close()
