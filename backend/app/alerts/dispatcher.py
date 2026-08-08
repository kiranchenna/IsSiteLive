import logging
from typing import Optional

from sqlalchemy.orm import Session

from app import models
from app.alerts import email as email_sender
from app.alerts import slack as slack_sender
from app.alerts import whatsapp as whatsapp_sender
from app.alerts.base import AlertMessage

logger = logging.getLogger("issitelive.alerts")

SENDERS = {
    models.AlertChannelType.slack: slack_sender.send,
    models.AlertChannelType.email: email_sender.send,
    models.AlertChannelType.whatsapp: whatsapp_sender.send,
}


def determine_alert_kind(current_status: models.RunStatus, previous_status: Optional[models.RunStatus]) -> Optional[str]:
    """Pure state-machine: fail alerts every time, recovery alerts once on fail->success, otherwise silent."""
    if current_status == models.RunStatus.fail:
        return "failure"
    if current_status == models.RunStatus.success and previous_status == models.RunStatus.fail:
        return "recovery"
    return None


def _resolve_channels(db: Session, site: models.Site) -> list[models.AlertChannel]:
    links = db.query(models.SiteAlertChannel).filter(models.SiteAlertChannel.site_id == site.id).all()
    if links:
        return [link.alert_channel for link in links]
    return db.query(models.AlertChannel).filter(models.AlertChannel.is_default.is_(True)).all()


def dispatch_alert_for_run(db: Session, check_run: models.CheckRun) -> None:
    site = db.get(models.Site, check_run.site_id)
    account = db.get(models.Account, check_run.account_id)

    previous_run = (
        db.query(models.CheckRun)
        .filter(models.CheckRun.site_id == site.id, models.CheckRun.account_id == account.id)
        .filter(models.CheckRun.id != check_run.id)
        .order_by(models.CheckRun.started_at.desc())
        .first()
    )
    previous_status = previous_run.status if previous_run else None

    kind = determine_alert_kind(check_run.status, previous_status)
    if kind is None:
        return

    message = AlertMessage(
        kind=kind,
        site_name=site.name,
        account_label=account.label,
        summary=check_run.error_summary or "Check passed",
        run_id=check_run.id,
        occurred_at=check_run.started_at.isoformat(),
    )

    for channel in _resolve_channels(db, site):
        sender = SENDERS.get(channel.type)
        if sender is None:
            continue  # a channel type with no registered sender
        try:
            sender(channel.config_json, message)
        except Exception:  # noqa: BLE001 - one broken channel must not block others or crash the check run
            logger.exception("Alert delivery failed for channel %s (%s, id=%s)", channel.label, channel.type.value, channel.id)
            continue
