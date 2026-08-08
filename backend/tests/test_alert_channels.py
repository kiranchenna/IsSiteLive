from app import models
from app.crypto import decrypt_password
from app.routers.alert_channels import _encrypt_smtp_password, _redact_smtp_password


def test_encrypt_smtp_password_for_email_channel():
    config = {"recipients": ["a@example.com"], "smtp_password": "supersecret"}
    result = _encrypt_smtp_password(models.AlertChannelType.email, config)
    assert result["smtp_password"] != "supersecret"
    assert decrypt_password(result["smtp_password"].encode()) == "supersecret"
    assert result["recipients"] == ["a@example.com"]


def test_encrypt_smtp_password_noop_when_absent():
    config = {"recipients": ["a@example.com"]}
    assert _encrypt_smtp_password(models.AlertChannelType.email, config) == config


def test_encrypt_smtp_password_ignored_for_non_email_channel():
    config = {"webhook_url": "https://hooks.slack.com/x", "smtp_password": "ignored"}
    result = _encrypt_smtp_password(models.AlertChannelType.slack, config)
    assert result["smtp_password"] == "ignored"  # untouched -- not an email channel


def test_redact_smtp_password_hides_the_encrypted_value():
    channel = models.AlertChannel(
        type=models.AlertChannelType.email,
        label="custom",
        config_json={"recipients": ["a@example.com"], "smtp_password": "gAAAAA-fake-token"},
    )
    redacted = _redact_smtp_password(channel)
    assert redacted.config_json["smtp_password"] is None
    assert redacted.config_json["smtp_password_set"] is True
    assert redacted.config_json["recipients"] == ["a@example.com"]


def test_redact_smtp_password_noop_when_using_shared_defaults():
    channel = models.AlertChannel(
        type=models.AlertChannelType.email,
        label="default",
        config_json={"recipients": ["a@example.com"]},
    )
    redacted = _redact_smtp_password(channel)
    assert "smtp_password_set" not in redacted.config_json
