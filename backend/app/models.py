import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.db import Base


class RunStatus(str, enum.Enum):
    running = "running"
    success = "success"
    fail = "fail"


class AlertChannelType(str, enum.Enum):
    slack = "slack"
    email = "email"
    whatsapp = "whatsapp"


class Site(Base):
    __tablename__ = "sites"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    base_url = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    check_interval_seconds = Column(Integer, default=300, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    flow = relationship("Flow", back_populates="site", uselist=False, cascade="all, delete-orphan")
    accounts = relationship("Account", back_populates="site", cascade="all, delete-orphan")
    check_runs = relationship("CheckRun", back_populates="site", cascade="all, delete-orphan")
    alert_channel_links = relationship("SiteAlertChannel", back_populates="site", cascade="all, delete-orphan")


class Flow(Base):
    __tablename__ = "flows"

    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, unique=True)
    steps_json = Column(JSON, nullable=False, default=list)
    watch_patterns_json = Column(JSON, nullable=False, default=list)  # list of {"pattern": str}
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    site = relationship("Site", back_populates="flow")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False)
    label = Column(String, nullable=False)
    username = Column(String, nullable=False)
    encrypted_password = Column(LargeBinary, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    site = relationship("Site", back_populates="accounts")
    check_runs = relationship("CheckRun", back_populates="account", cascade="all, delete-orphan")


class CheckRun(Base):
    __tablename__ = "check_runs"

    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    status = Column(Enum(RunStatus), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    error_summary = Column(Text, nullable=True)

    site = relationship("Site", back_populates="check_runs")
    account = relationship("Account", back_populates="check_runs")
    step_results = relationship("StepResult", back_populates="check_run", cascade="all, delete-orphan")


class StepResult(Base):
    __tablename__ = "step_results"

    id = Column(Integer, primary_key=True)
    check_run_id = Column(Integer, ForeignKey("check_runs.id"), nullable=False)
    step_index = Column(Integer, nullable=False)
    step_type = Column(String, nullable=False)
    status = Column(Enum(RunStatus), nullable=False)
    http_status = Column(Integer, nullable=True)
    message = Column(Text, nullable=True)
    screenshot_path = Column(String, nullable=True)

    check_run = relationship("CheckRun", back_populates="step_results")


class AlertChannel(Base):
    __tablename__ = "alert_channels"

    id = Column(Integer, primary_key=True)
    type = Column(Enum(AlertChannelType), nullable=False)
    label = Column(String, nullable=False)
    config_json = Column(JSON, nullable=False, default=dict)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    site_links = relationship("SiteAlertChannel", back_populates="alert_channel", cascade="all, delete-orphan")


class SiteAlertChannel(Base):
    __tablename__ = "site_alert_channels"

    site_id = Column(Integer, ForeignKey("sites.id"), primary_key=True)
    alert_channel_id = Column(Integer, ForeignKey("alert_channels.id"), primary_key=True)

    site = relationship("Site", back_populates="alert_channel_links")
    alert_channel = relationship("AlertChannel", back_populates="site_links")
