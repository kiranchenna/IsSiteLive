import smtplib
from email.mime.text import MIMEText

from app.alerts.base import AlertMessage
from app.config import settings


def send(config: dict, message: AlertMessage) -> None:
    recipients = config.get("recipients", [])
    if not recipients:
        return

    title = "Check failed" if message.kind == "failure" else "Recovered"
    subject = f"[IsSiteLive] {title}: {message.site_name} ({message.account_label})"
    body = f"{message.summary}\n\nRun #{message.run_id} at {message.occurred_at}"

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = ", ".join(recipients)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password)
        server.sendmail(settings.smtp_from, recipients, msg.as_string())
