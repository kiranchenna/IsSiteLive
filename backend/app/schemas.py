from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.models import AlertChannelType, RunStatus


# ---- Site ----
class SiteBase(BaseModel):
    name: str
    base_url: str
    is_active: bool = True
    check_interval_seconds: int = 300


class SiteCreate(SiteBase):
    pass


class SiteUpdate(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    is_active: Optional[bool] = None
    check_interval_seconds: Optional[int] = None


class SiteOut(SiteBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    next_run_at: Optional[datetime] = None


# ---- Flow ----
class FlowUpsert(BaseModel):
    steps_json: list[dict[str, Any]]
    watch_patterns_json: list[dict[str, Any]] = []


class FlowOut(FlowUpsert):
    model_config = ConfigDict(from_attributes=True)
    id: int
    site_id: int


# ---- Account ----
class AccountCreate(BaseModel):
    label: str
    username: str
    password: str
    is_active: bool = True


class AccountUpdate(BaseModel):
    label: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    site_id: int
    label: str
    username: str
    is_active: bool
    created_at: datetime


# ---- AlertChannel ----
class AlertChannelCreate(BaseModel):
    type: AlertChannelType
    label: str
    config_json: dict[str, Any]
    is_default: bool = False


class AlertChannelUpdate(BaseModel):
    label: Optional[str] = None
    config_json: Optional[dict[str, Any]] = None
    is_default: Optional[bool] = None


class AlertChannelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: AlertChannelType
    label: str
    config_json: dict[str, Any]
    is_default: bool
    created_at: datetime


class SiteAlertChannelsUpdate(BaseModel):
    alert_channel_ids: list[int]


# ---- CheckRun / StepResult ----
class StepResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    step_index: int
    step_type: str
    status: RunStatus
    http_status: Optional[int]
    message: Optional[str]
    screenshot_path: Optional[str]


class CheckRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    site_id: int
    account_id: int
    status: RunStatus
    started_at: datetime
    finished_at: Optional[datetime]
    duration_ms: Optional[int]
    error_summary: Optional[str]


class CheckRunDetailOut(CheckRunOut):
    step_results: list[StepResultOut]


class SiteStatusOut(BaseModel):
    site_id: int
    site_name: str
    is_active: bool
    next_run_at: Optional[datetime] = None
    accounts: list[dict[str, Any]]  # [{account_id, label, last_status, last_run_at}]
