from app.alerts.dispatcher import determine_alert_kind
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
