import httpx

from app.alerts.base import AlertMessage

EMOJI = {"failure": ":red_circle:", "recovery": ":large_green_circle:"}


def send(config: dict, message: AlertMessage) -> None:
    webhook_url = config["webhook_url"]
    emoji = EMOJI.get(message.kind, "")
    title = "Check failed" if message.kind == "failure" else "Recovered"
    text = (
        f"{emoji} *{title}* — {message.site_name} ({message.account_label})\n"
        f"{message.summary}\n"
        f"Run #{message.run_id} at {message.occurred_at}"
    )
    httpx.post(webhook_url, json={"text": text}, timeout=10)
