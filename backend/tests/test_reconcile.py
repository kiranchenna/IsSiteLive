from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.db import Base, reconcile_interrupted_runs


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/reconcile_test.db")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _make_run(db, status):
    site = models.Site(name="Test", base_url="https://example.com")
    account = models.Account(site=site, label="demo", username="u", encrypted_password=b"x")
    db.add_all([site, account])
    db.flush()
    run = models.CheckRun(site_id=site.id, account_id=account.id, status=status, started_at=datetime.utcnow())
    db.add(run)
    db.commit()
    return run


def test_stuck_running_runs_are_marked_failed(db_session):
    stuck = _make_run(db_session, models.RunStatus.running)
    finished = _make_run(db_session, models.RunStatus.success)

    count = reconcile_interrupted_runs(db_session)

    assert count == 1
    db_session.refresh(stuck)
    db_session.refresh(finished)
    assert stuck.status == models.RunStatus.fail
    assert "Interrupted" in stuck.error_summary
    assert stuck.finished_at is not None
    assert finished.status == models.RunStatus.success  # untouched


def test_no_stuck_runs_is_a_noop(db_session):
    _make_run(db_session, models.RunStatus.success)
    assert reconcile_interrupted_runs(db_session) == 0
