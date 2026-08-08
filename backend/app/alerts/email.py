import smtplib
from email.mime.text import MIMEText

from app.alerts.base import AlertMessage
from app.config import settings
from app.crypto import decrypt_password


def _server_settings(config: dict) -> dict:
    """A channel can bring its own mail server (e.g. a personal Gmail account or a service
    like SendGrid) instead of relying on whatever the deployment's admin configured server-
    wide -- set any of these on the channel and they override the shared default for that
    field alone, so e.g. a custom "from" address doesn't require also setting a password."""
    password = config.get("smtp_password")
    return {
        "host": config.get("smtp_host") or settings.smtp_host,
        "port": config.get("smtp_port") or settings.smtp_port,
        "username": config.get("smtp_username") or settings.smtp_username,
        "password": decrypt_password(password.encode()) if password else settings.smtp_password,
        "from_addr": config.get("smtp_from") or settings.smtp_from,
        "use_tls": config.get("smtp_use_tls", settings.smtp_use_tls),
    }


def send(config: dict, message: AlertMessage) -> None:
    recipients = config.get("recipients", [])
    if not recipients:
        return

    server_settings = _server_settings(config)

    title = "Check failed" if message.kind == "failure" else "Recovered"
    subject = f"[IsSiteLive] {title}: {message.site_name} ({message.account_label})"
    body = f"{message.summary}\n\nRun #{message.run_id} at {message.occurred_at}"

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = server_settings["from_addr"]
    msg["To"] = ", ".join(recipients)

    with smtplib.SMTP(server_settings["host"], server_settings["port"]) as server:
        if server_settings["use_tls"]:
            server.starttls()
        if server_settings["username"]:
            server.login(server_settings["username"], server_settings["password"])
        server.sendmail(server_settings["from_addr"], recipients, msg.as_string())
