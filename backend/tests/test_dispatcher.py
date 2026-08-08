from datetime import datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.alerts import dispatcher
from app.alerts.dispatcher import determine_alert_kind
from app.db import Base
from app.models import RunStatus


def test_failure_alerts_every_time():
    assert determine_alert_kind(RunStatus.fail, None) == "failure"
    assert determine_alert_kind(RunStatus.fail, RunStatus.fail) == "failure"
    assert determine_alert_kind(RunStatus.fail, RunStatus.success) == "failure"


def test_recovery_alerts_once_on_transition():
    assert determine_alert_kind(RunStatus.success, RunStatus.fail) == "recovery"


def test_repeated_success_is_silent():
    assert determine_alert_kind(RunStatus.success, RunStatus.success) is None


def test_first_ever_success_is_silent():
    assert determine_alert_kind(RunStatus.success, None) is None


def test_success_after_a_stuck_running_previous_run_is_silent():
    """A previous run can be stuck at "running" if the process died mid-check; that must
    not be treated as a prior failure once a startup reconciliation resolves it, but even
    before that happens this should stay silent rather than firing a bogus recovery alert."""
    assert determine_alert_kind(RunStatus.success, RunStatus.running) is None


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/dispatcher_test.db")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def test_one_broken_channel_does_not_block_the_others(db_session, monkeypatch, caplog):
    site = models.Site(name="Test", base_url="https://example.com")
    account = models.Account(site=site, label="demo", username="u", encrypted_password=b"x")
    db_session.add_all([site, account])
    db_session.flush()

    broken = models.AlertChannel(type=models.AlertChannelType.slack, label="broken", config_json={}, is_default=True)
    working = models.AlertChannel(type=models.AlertChannelType.email, label="working", config_json={}, is_default=True)
    db_session.add_all([broken, working])
    db_session.flush()

    run = models.CheckRun(
        site_id=site.id, account_id=account.id, status=models.RunStatus.fail, started_at=datetime.utcnow(),
        error_summary="down",
    )
    db_session.add(run)
    db_session.commit()

    broken_sender = MagicMock(side_effect=RuntimeError("bad webhook"))
    working_sender = MagicMock()
    monkeypatch.setitem(dispatcher.SENDERS, models.AlertChannelType.slack, broken_sender)
    monkeypatch.setitem(dispatcher.SENDERS, models.AlertChannelType.email, working_sender)

    with caplog.at_level("ERROR"):
        dispatcher.dispatch_alert_for_run(db_session, run)

    broken_sender.assert_called_once()
    working_sender.assert_called_once()  # still ran despite the other channel raising
    assert "broken" in caplog.text  # the failure was logged, not silently swallowed
