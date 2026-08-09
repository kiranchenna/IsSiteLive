import asyncio
import base64

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models
from app.crypto import decrypt_password
from app.db import get_db
from app.recorder import manager

router = APIRouter(tags=["recordings"])


class StartRecordingRequest(BaseModel):
    account_id: int


@router.post("/api/sites/{site_id}/recordings", status_code=201)
async def start_recording(site_id: int, payload: StartRecordingRequest, db: Session = Depends(get_db)):
    site = db.get(models.Site, site_id)
    if not site:
        raise HTTPException(404, "Site not found")
    account = db.get(models.Account, payload.account_id)
    if not account or account.site_id != site_id:
        raise HTTPException(404, "Account not found for this site")
    password = decrypt_password(account.encrypted_password)
    try:
        session = await manager.create_session(username=account.username, password=password, start_url=site.base_url)
    except Exception as exc:  # noqa: BLE001 - surface as a clean error rather than a raw 500
        raise HTTPException(502, f"Could not open {site.base_url}: {exc}") from exc
    return {"session_id": session.session_id}


@router.get("/api/recordings/{session_id}/steps")
def get_recording_steps(session_id: str):
    session = manager.get_session(session_id)
    if not session:
        raise HTTPException(404, "Recording session not found")
    return {"steps": session.steps}


@router.delete("/api/recordings/{session_id}", status_code=204)
async def stop_recording(session_id: str):
    await manager.remove_session(session_id)


@router.websocket("/api/recordings/{session_id}/stream")
async def recording_stream(websocket: WebSocket, session_id: str):
    session = manager.get_session(session_id)
    if not session:
        await websocket.close(code=4404)
        return

    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue()

    session.on_frame = lambda data: queue.put_nowait(
        {"type": "frame", "data": base64.b64encode(data).decode()}
    )
    session.on_step = lambda step, replace: queue.put_nowait(
        {"type": "step", "step": step, "replace_last": replace}
    )
    session.on_url = lambda url: queue.put_nowait({"type": "url", "url": url})

    bootstrap_frame = await session.capture_bootstrap_frame()
    if bootstrap_frame:
        await queue.put({"type": "frame", "data": base64.b64encode(bootstrap_frame).decode()})

    async def sender():
        while True:
            message = await queue.get()
            await websocket.send_json(message)

    sender_task = asyncio.create_task(sender())
    try:
        while True:
            message = await websocket.receive_json()
            kind = message.get("type")
            if kind == "mouse":
                await session.dispatch_mouse(
                    message["x"], message["y"], message["kind"], message.get("button", "left")
                )
            elif kind == "text":
                await session.dispatch_text(message["text"])
            elif kind == "key":
                await session.dispatch_key(message["key"], message["kind"])
            elif kind == "mark_success":
                session.mark_next_click_as_success()
            elif kind == "mark_assertion":
                session.mark_next_click_as_assertion(message.get("value", ""))
            elif kind == "stop":
                await manager.remove_session(session_id)
                break
    except WebSocketDisconnect:
        pass
    finally:
        sender_task.cancel()
        session.on_frame = None
        session.on_step = None
        session.on_url = None
