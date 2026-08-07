from dataclasses import dataclass
from typing import Protocol


@dataclass
class AlertMessage:
    kind: str  # "failure" | "recovery"
    site_name: str
    account_label: str
    summary: str
    run_id: int
    occurred_at: str


class AlertSender(Protocol):
    def send(self, config: dict, message: AlertMessage) -> None: ...
