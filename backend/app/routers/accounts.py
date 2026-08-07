from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.crypto import encrypt_password
from app.db import get_db

router = APIRouter(tags=["accounts"])


@router.get("/api/sites/{site_id}/accounts", response_model=list[schemas.AccountOut])
def list_accounts(site_id: int, db: Session = Depends(get_db)):
    return db.query(models.Account).filter(models.Account.site_id == site_id).all()


@router.post("/api/sites/{site_id}/accounts", response_model=schemas.AccountOut, status_code=201)
def create_account(site_id: int, payload: schemas.AccountCreate, db: Session = Depends(get_db)):
    site = db.get(models.Site, site_id)
    if not site:
        raise HTTPException(404, "Site not found")
    account = models.Account(
        site_id=site_id,
        label=payload.label,
        username=payload.username,
        encrypted_password=encrypt_password(payload.password),
        is_active=payload.is_active,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.put("/api/accounts/{account_id}", response_model=schemas.AccountOut)
def update_account(account_id: int, payload: schemas.AccountUpdate, db: Session = Depends(get_db)):
    account = db.get(models.Account, account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    data = payload.model_dump(exclude_unset=True)
    if "password" in data:
        account.encrypted_password = encrypt_password(data.pop("password"))
    for field, value in data.items():
        setattr(account, field, value)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/api/accounts/{account_id}", status_code=204)
def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = db.get(models.Account, account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    db.delete(account)
    db.commit()
