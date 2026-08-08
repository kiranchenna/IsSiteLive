from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.crypto import encrypt_password
from app.db import get_db

router = APIRouter(prefix="/api/alert-channels", tags=["alert-channels"])


def _encrypt_smtp_password(channel_type: models.AlertChannelType, config_json: dict) -> dict:
    """A per-channel SMTP password is real mail-account credentials, not a webhook URL --
    it gets the same Fernet encryption-at-rest as demo account passwords, not stored plain."""
    if channel_type == models.AlertChannelType.email and config_json.get("smtp_password"):
        config_json = {**config_json, "smtp_password": encrypt_password(config_json["smtp_password"]).decode()}
    return config_json


def _redact_smtp_password(channel: models.AlertChannel) -> models.AlertChannel:
    """Never send the encrypted password back to the client -- callers only need to know
    whether custom SMTP is configured, not the credential itself."""
    if channel.type == models.AlertChannelType.email and channel.config_json.get("smtp_password"):
        channel.config_json = {**channel.config_json, "smtp_password": None, "smtp_password_set": True}
    return channel


@router.get("", response_model=list[schemas.AlertChannelOut])
def list_channels(db: Session = Depends(get_db)):
    return [_redact_smtp_password(c) for c in db.query(models.AlertChannel).all()]


@router.post("", response_model=schemas.AlertChannelOut, status_code=201)
def create_channel(payload: schemas.AlertChannelCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    data["config_json"] = _encrypt_smtp_password(data["type"], data["config_json"])
    channel = models.AlertChannel(**data)
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return _redact_smtp_password(channel)


@router.put("/{channel_id}", response_model=schemas.AlertChannelOut)
def update_channel(channel_id: int, payload: schemas.AlertChannelUpdate, db: Session = Depends(get_db)):
    channel = db.get(models.AlertChannel, channel_id)
    if not channel:
        raise HTTPException(404, "Alert channel not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "config_json" and value is not None:
            value = _encrypt_smtp_password(channel.type, value)
        setattr(channel, field, value)
    db.commit()
    db.refresh(channel)
    return _redact_smtp_password(channel)


@router.delete("/{channel_id}", status_code=204)
def delete_channel(channel_id: int, db: Session = Depends(get_db)):
    channel = db.get(models.AlertChannel, channel_id)
    if not channel:
        raise HTTPException(404, "Alert channel not found")
    db.delete(channel)
    db.commit()
