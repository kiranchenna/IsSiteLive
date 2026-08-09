import asyncio
import base64
import time
from typing import Any, Callable, Optional

from playwright.async_api import async_playwright

from app.recorder.selector_script import RECORDER_INIT_SCRIPT

VIEWPORT = {"width": 1280, "height": 800}
IDLE_TIMEOUT_SECONDS = 600


class RecordingSession:
    def __init__(self, session_id: str, username: str, password: str):
        self.session_id = session_id
        self.username = username
        self.password = password
        self.steps: list[dict[str, Any]] = []
        self.last_activity = time.monotonic()

        self.on_frame: Optional[Callable[[bytes], None]] = None
        self.on_step: Optional[Callable[[dict, bool], None]] = None  # (step, replace_last)
        self.on_url: Optional[Callable[[str], None]] = None

        self._marking_success = False
        self._marking_assertion_value: Optional[str] = None
        self._initial_navigate_recorded = False
        self._playwright = None
        self._browser = None
        self._page = None
        self._cdp = None

    def is_idle(self) -> bool:
        return (time.monotonic() - self.last_activity) > IDLE_TIMEOUT_SECONDS

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        context = await self._browser.new_context(viewport=VIEWPORT)
        self._page = await context.new_page()
        await self._page.add_init_script(RECORDER_INIT_SCRIPT)
        await self._page.expose_binding("__record", self._handle_record)
        self._page.on("framenavigated", self._handle_navigation)

        self._cdp = await context.new_cdp_session(self._page)
        self._cdp.on("Page.screencastFrame", self._handle_screencast_frame)
        await self._cdp.send(
            "Page.startScreencast",
            {
                "format": "jpeg",
                "quality": 60,
                "maxWidth": VIEWPORT["width"],
                "maxHeight": VIEWPORT["height"],
                "everyNthFrame": 1,
            },
        )
        await self._page.goto("about:blank")

    async def navigate(self, url: str) -> None:
        # domcontentloaded rather than the default "load": real sites often keep the load
        # event pending on slow-loading trackers/analytics long after the page is actually
        # usable, which would otherwise time out a recording session before it even starts.
        await self._page.goto(url, wait_until="domcontentloaded", timeout=45000)

    async def capture_bootstrap_frame(self) -> Optional[bytes]:
        """CDP screencast only pushes a frame on repaint, so a client that connects after the
        page has already settled would otherwise see nothing until something changes."""
        if self._cdp is None:
            return None
        result = await self._cdp.send("Page.captureScreenshot", {"format": "jpeg", "quality": 60})
        data = result.get("data")
        return base64.b64decode(data) if data else None

    def mark_next_click_as_success(self) -> None:
        self._marking_success = True

    def mark_next_click_as_assertion(self, value: str) -> None:
        self._marking_assertion_value = value

    def _append_step(self, step: dict[str, Any], replace_last: bool = False) -> None:
        if replace_last and self.steps:
            self.steps[-1] = step
        else:
            self.steps.append(step)
        if self.on_step:
            self.on_step(step, replace_last)

    def _handle_navigation(self, frame) -> None:
        if frame != self._page.main_frame:
            return
        url = frame.url
        if url in ("about:blank", ""):
            return
        self.last_activity = time.monotonic()
        if not self._initial_navigate_recorded:
            # Only the very first navigation is recorded as an explicit step. Every later
            # navigation -- SSO redirects, OAuth callbacks, form submissions -- happens as a
            # side effect of a click step and gets replayed for free when that click runs
            # again. Recording them as literal navigate steps would hardcode one-time-use
            # tokens (OAuth `code`, `state`, `session_state`) straight into the flow, which
            # are already consumed after the recording session and make replay fail every
            # time by bouncing back to the login page.
            self._initial_navigate_recorded = True
            self._append_step({"type": "navigate", "url": url})
        if self.on_url:
            self.on_url(url)

    async def _handle_record(self, source, payload: dict[str, Any]) -> None:
        self.last_activity = time.monotonic()
        action_type = payload.get("type")
        selector = payload.get("selector")
        if not selector:
            return

        if self._marking_success:
            self._marking_success = False
            self._append_step({"type": "wait_for_selector", "selector": selector, "timeout_ms": 15000})
            return

        if self._marking_assertion_value is not None:
            value = self._marking_assertion_value
            self._marking_assertion_value = None
            self._append_step({"type": "assert_text_contains", "selector": selector, "value": value})
            return

        if selector in ("body", "html"):
            return  # background click during normal recording, not meaningful on its own

        if action_type == "click":
            self._append_step({"type": "click", "selector": selector})
        elif action_type == "fill":
            value = payload.get("value", "")
            if self.username and value == self.username:
                value = "{{username}}"
            elif self.password and value == self.password:
                value = "{{password}}"

            if self.steps and self.steps[-1].get("type") == "fill" and self.steps[-1].get("selector") == selector:
                self._append_step({"type": "fill", "selector": selector, "value": value}, replace_last=True)
            else:
                self._append_step({"type": "fill", "selector": selector, "value": value})

    def _handle_screencast_frame(self, event: dict[str, Any]) -> None:
        session_id = event.get("sessionId")
        data = event.get("data")
        asyncio.create_task(self._ack_frame(session_id))
        if data and self.on_frame:
            self.on_frame(base64.b64decode(data))

    async def _ack_frame(self, session_id) -> None:
        if self._cdp is None:
            return
        try:
            await self._cdp.send("Page.screencastFrameAck", {"sessionId": session_id})
        except Exception:  # noqa: BLE001 - session may already be closing
            pass

    async def dispatch_mouse(self, x: float, y: float, kind: str, button: str = "left") -> None:
        self.last_activity = time.monotonic()
        cdp_type = {"move": "mouseMoved", "down": "mousePressed", "up": "mouseReleased"}.get(kind)
        if not cdp_type or self._cdp is None:
            return
        await self._cdp.send(
            "Input.dispatchMouseEvent",
            {
                "type": cdp_type,
                "x": x,
                "y": y,
                "button": button,
                "clickCount": 1 if kind != "move" else 0,
            },
        )

    async def dispatch_text(self, text: str) -> None:
        self.last_activity = time.monotonic()
        if self._cdp is None:
            return
        await self._cdp.send("Input.insertText", {"text": text})

    async def dispatch_key(self, key: str, kind: str) -> None:
        self.last_activity = time.monotonic()
        if self._cdp is None:
            return
        cdp_type = "keyDown" if kind == "down" else "keyUp"
        await self._cdp.send("Input.dispatchKeyEvent", {"type": cdp_type, "key": key})

    async def stop(self) -> None:
        try:
            if self._cdp:
                await self._cdp.send("Page.stopScreencast")
        except Exception:  # noqa: BLE001 - best-effort cleanup
            pass
        try:
            if self._browser:
                await self._browser.close()
        except Exception:  # noqa: BLE001
            pass
        if self._playwright:
            await self._playwright.stop()
