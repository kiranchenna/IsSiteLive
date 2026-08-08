from unittest.mock import MagicMock, patch

from app.alerts.base import AlertMessage
from app.alerts.email import send
from app.crypto import encrypt_password

MESSAGE = AlertMessage(
    kind="failure", site_name="TinyMedic", account_label="demo", summary="down", run_id=1, occurred_at="2026-01-01T00:00:00"
)


def _global_settings(mock_settings):
    mock_settings.smtp_host = "global.smtp.test"
    mock_settings.smtp_port = 25
    mock_settings.smtp_username = ""
    mock_settings.smtp_password = ""
    mock_settings.smtp_from = "alerts@global.test"
    mock_settings.smtp_use_tls = False


@patch("app.alerts.email.smtplib.SMTP")
@patch("app.alerts.email.settings")
def test_falls_back_to_shared_server_settings_when_channel_has_none(mock_settings, mock_smtp_cls):
    _global_settings(mock_settings)
    mock_server = MagicMock()
    mock_smtp_cls.return_value.__enter__.return_value = mock_server

    send({"recipients": ["a@example.com"]}, MESSAGE)

    mock_smtp_cls.assert_called_once_with("global.smtp.test", 25)
    mock_server.starttls.assert_not_called()
    mock_server.login.assert_not_called()
    assert mock_server.sendmail.call_args[0][0] == "alerts@global.test"


@patch("app.alerts.email.smtplib.SMTP")
@patch("app.alerts.email.settings")
def test_uses_the_channels_own_mail_server_when_provided(mock_settings, mock_smtp_cls):
    _global_settings(mock_settings)
    mock_server = MagicMock()
    mock_smtp_cls.return_value.__enter__.return_value = mock_server
    encrypted_pw = encrypt_password("my-app-password").decode()

    send(
        {
            "recipients": ["a@example.com"],
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_username": "me@gmail.com",
            "smtp_password": encrypted_pw,
            "smtp_from": "me@gmail.com",
            "smtp_use_tls": True,
        },
        MESSAGE,
    )

    mock_smtp_cls.assert_called_once_with("smtp.gmail.com", 587)
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("me@gmail.com", "my-app-password")
    assert mock_server.sendmail.call_args[0][0] == "me@gmail.com"


@patch("app.alerts.email.smtplib.SMTP")
@patch("app.alerts.email.settings")
def test_partial_override_only_replaces_the_fields_given(mock_settings, mock_smtp_cls):
    """Setting a custom "from" address shouldn't force also configuring a password --
    each field falls back to the shared default independently."""
    _global_settings(mock_settings)
    mock_settings.smtp_username = "shared-user"
    mock_settings.smtp_password = "shared-pass"
    mock_server = MagicMock()
    mock_smtp_cls.return_value.__enter__.return_value = mock_server

    send({"recipients": ["a@example.com"], "smtp_from": "custom@example.com"}, MESSAGE)

    mock_smtp_cls.assert_called_once_with("global.smtp.test", 25)  # host/port still shared
    mock_server.login.assert_called_once_with("shared-user", "shared-pass")  # creds still shared
    assert mock_server.sendmail.call_args[0][0] == "custom@example.com"  # from overridden
