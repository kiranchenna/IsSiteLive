from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.db import get_db

router = APIRouter(prefix="/api/alert-channels", tags=["alert-channels"])


@router.get("", response_model=list[schemas.AlertChannelOut])
def list_channels(db: Session = Depends(get_db)):
    return db.query(models.AlertChannel).all()


@router.post("", response_model=schemas.AlertChannelOut, status_code=201)
def create_channel(payload: schemas.AlertChannelCreate, db: Session = Depends(get_db)):
    channel = models.AlertChannel(**payload.model_dump())
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return channel


@router.put("/{channel_id}", response_model=schemas.AlertChannelOut)
def update_channel(channel_id: int, payload: schemas.AlertChannelUpdate, db: Session = Depends(get_db)):
    channel = db.get(models.AlertChannel, channel_id)
    if not channel:
        raise HTTPException(404, "Alert channel not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(channel, field, value)
    db.commit()
    db.refresh(channel)
    return channel


@router.delete("/{channel_id}", status_code=204)
def delete_channel(channel_id: int, db: Session = Depends(get_db)):
    channel = db.get(models.AlertChannel, channel_id)
    if not channel:
        raise HTTPException(404, "Alert channel not found")
    db.delete(channel)
    db.commit()
