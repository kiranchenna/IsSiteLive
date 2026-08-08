"""Sends alerts via Twilio's WhatsApp API.

WhatsApp does not allow plain business-initiated messages the way Slack/email do -- outbound
messages outside an active 24h customer-service window (i.e. essentially all of ours, since
these are proactive alerts, not replies) require either:

  1. The Twilio Sandbox, which accepts free-text `Body` messages for development/testing
     once the recipient has joined the sandbox -- no approval needed, good for getting
     started immediately.
  2. An approved WhatsApp message Template in production, referenced by its Content SID,
     with the alert text passed as the template's first variable.

A channel's config_json controls which mode is used: if `content_sid` is set, template mode
is used; otherwise the message is sent as free-text `Body` (sandbox mode).
"""
import json

import httpx

from app.alerts.base import AlertMessage
from app.config import settings

TWILIO_MESSAGES_URL = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


def _alert_text(message: AlertMessage) -> str:
    title = "Check failed" if message.kind == "failure" else "Recovered"
    return f"{title}: {message.site_name} ({message.account_label}) — {message.summary}"


def send(config: dict, message: AlertMessage) -> None:
    recipients = config.get("recipients", [])
    if not recipients or not settings.twilio_account_sid or not settings.twilio_whatsapp_from:
        return

    text = _alert_text(message)
    content_sid = config.get("content_sid")
    url = TWILIO_MESSAGES_URL.format(sid=settings.twilio_account_sid)

    for recipient in recipients:
        data = {
            "From": f"whatsapp:{settings.twilio_whatsapp_from}",
            "To": f"whatsapp:{recipient}",
        }
        if content_sid:
            data["ContentSid"] = content_sid
            data["ContentVariables"] = json.dumps({"1": text})
        else:
            data["Body"] = text

        httpx.post(url, data=data, auth=(settings.twilio_account_sid, settings.twilio_auth_token), timeout=10)
