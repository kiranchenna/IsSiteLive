from unittest.mock import patch

from app.alerts.base import AlertMessage
from app.alerts.whatsapp import send

MESSAGE = AlertMessage(
    kind="failure",
    site_name="TinyMedic",
    account_label="demo",
    summary="Step 2 (click) failed: timeout",
    run_id=42,
    occurred_at="2026-08-08T10:00:00",
)


def _settings(**overrides):
    defaults = dict(twilio_account_sid="ACxxx", twilio_auth_token="secret", twilio_whatsapp_from="+14155238886")
    defaults.update(overrides)
    return defaults


@patch("app.alerts.whatsapp.httpx.post")
@patch("app.alerts.whatsapp.settings")
def test_sandbox_mode_sends_freeform_body(mock_settings, mock_post):
    for k, v in _settings().items():
        setattr(mock_settings, k, v)

    send({"recipients": ["+919876543210"]}, MESSAGE)

    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    assert kwargs["data"]["To"] == "whatsapp:+919876543210"
    assert kwargs["data"]["From"] == "whatsapp:+14155238886"
    assert "Body" in kwargs["data"]
    assert "ContentSid" not in kwargs["data"]
    assert "TinyMedic" in kwargs["data"]["Body"]


@patch("app.alerts.whatsapp.httpx.post")
@patch("app.alerts.whatsapp.settings")
def test_template_mode_sends_content_sid_and_variables(mock_settings, mock_post):
    for k, v in _settings().items():
        setattr(mock_settings, k, v)

    send({"recipients": ["+919876543210"], "content_sid": "HXabc123"}, MESSAGE)

    _, kwargs = mock_post.call_args
    assert kwargs["data"]["ContentSid"] == "HXabc123"
    assert "Body" not in kwargs["data"]
    assert "TinyMedic" in kwargs["data"]["ContentVariables"]


@patch("app.alerts.whatsapp.httpx.post")
@patch("app.alerts.whatsapp.settings")
def test_sends_to_every_recipient(mock_settings, mock_post):
    for k, v in _settings().items():
        setattr(mock_settings, k, v)

    send({"recipients": ["+91111", "+91222", "+91333"]}, MESSAGE)

    assert mock_post.call_count == 3


@patch("app.alerts.whatsapp.httpx.post")
@patch("app.alerts.whatsapp.settings")
def test_noop_without_recipients(mock_settings, mock_post):
    for k, v in _settings().items():
        setattr(mock_settings, k, v)

    send({"recipients": []}, MESSAGE)

    mock_post.assert_not_called()


@patch("app.alerts.whatsapp.httpx.post")
@patch("app.alerts.whatsapp.settings")
def test_noop_when_twilio_not_configured(mock_settings, mock_post):
    for k, v in _settings(twilio_account_sid="").items():
        setattr(mock_settings, k, v)

    send({"recipients": ["+919876543210"]}, MESSAGE)

    mock_post.assert_not_called()
