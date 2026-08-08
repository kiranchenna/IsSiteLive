from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.db import Base
from app.retention import sweep_expired_screenshots


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/retention_test.db")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture()
def screenshots_dir(tmp_path, monkeypatch):
    import app.retention as retention_module

    directory = tmp_path / "screenshots"
    directory.mkdir()
    monkeypatch.setattr(retention_module.settings, "screenshots_dir", str(directory))
    return directory


def _make_run(db, started_at, screenshot_names):
    site = models.Site(name="Test", base_url="https://example.com")
    account = models.Account(site=site, label="demo", username="u", encrypted_password=b"x")
    db.add_all([site, account])
    db.flush()

    run = models.CheckRun(site_id=site.id, account_id=account.id, status=models.RunStatus.success, started_at=started_at)
    db.add(run)
    db.flush()

    for i, name in enumerate(screenshot_names):
        db.add(
            models.StepResult(
                check_run_id=run.id,
                step_index=i,
                step_type="navigate",
                status=models.RunStatus.success,
                screenshot_path=f"/screenshots/{name}" if name else None,
            )
        )
    db.commit()
    return run


def test_sweep_deletes_files_and_clears_paths_for_old_runs_only(db_session, screenshots_dir):
    old_file = screenshots_dir / "old.png"
    old_file.write_bytes(b"fake")
    recent_file = screenshots_dir / "recent.png"
    recent_file.write_bytes(b"fake")

    _make_run(db_session, datetime.utcnow() - timedelta(days=200), ["old.png"])
    _make_run(db_session, datetime.utcnow() - timedelta(days=1), ["recent.png"])

    result = sweep_expired_screenshots(db_session, days=180)

    assert result == {"retention_days": 180, "cleared_step_results": 1, "deleted_files": 1}
    assert not old_file.exists()
    assert recent_file.exists()

    paths = [s.screenshot_path for s in db_session.query(models.StepResult).all()]
    assert paths.count(None) == 1
    assert "/screenshots/recent.png" in paths


def test_sweep_falls_back_to_configured_default_when_days_not_given(db_session, screenshots_dir):
    import app.retention as retention_module

    old_file = screenshots_dir / "old.png"
    old_file.write_bytes(b"fake")
    _make_run(db_session, datetime.utcnow() - timedelta(days=200), ["old.png"])

    assert retention_module.settings.screenshot_retention_days == 180
    result = sweep_expired_screenshots(db_session)  # no `days` -- must apply the default

    assert result["retention_days"] == 180
    assert result["cleared_step_results"] == 1


def test_sweep_is_safe_when_file_already_missing(db_session, screenshots_dir):
    _make_run(db_session, datetime.utcnow() - timedelta(days=200), ["already_gone.png"])

    result = sweep_expired_screenshots(db_session, days=180)

    assert result == {"retention_days": 180, "cleared_step_results": 1, "deleted_files": 0}
