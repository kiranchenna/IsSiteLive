import os

import pytest

from app.recorder import manager as recorder_manager
from app.recorder.session import RecordingSession

FIXTURE_PATH = "file://" + os.path.join(os.path.dirname(__file__), "fixtures", "login_form.html")
NAV_START_PATH = "file://" + os.path.join(os.path.dirname(__file__), "fixtures", "nav_start.html")
FORM_LIST_PATH = "file://" + os.path.join(os.path.dirname(__file__), "fixtures", "form_list.html")


async def _click(session: RecordingSession, selector: str):
    box = await session._page.locator(selector).bounding_box()
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    await session.dispatch_mouse(x, y, "move")
    await session.dispatch_mouse(x, y, "down")
    await session.dispatch_mouse(x, y, "up")
    await session._page.wait_for_timeout(50)


@pytest.mark.asyncio
async def test_records_navigate_click_fill_and_success_marker():
    session = RecordingSession("test-session", username="demo_user", password="demo_pass")
    await session.start()
    try:
        await session._page.goto(FIXTURE_PATH)
        await session._page.wait_for_timeout(50)

        await _click(session, "#username")
        await session.dispatch_text("demo_user")
        await session._page.wait_for_timeout(50)

        await _click(session, "#password")
        await session.dispatch_text("demo_pass")
        await session._page.wait_for_timeout(50)

        await _click(session, "#submit")

        session.mark_next_click_as_success()
        await _click(session, "#dashboard")

        await session._page.wait_for_timeout(200)

        types = [s["type"] for s in session.steps]
        assert types == ["navigate", "click", "fill", "click", "fill", "click", "wait_for_selector"]

        fill_steps = [s for s in session.steps if s["type"] == "fill"]
        assert fill_steps[0]["selector"] == "#username"
        assert fill_steps[0]["value"] == "{{username}}"
        assert fill_steps[1]["selector"] == "#password"
        assert fill_steps[1]["value"] == "{{password}}"

        assert session.steps[-1] == {"type": "wait_for_selector", "selector": "#dashboard", "timeout_ms": 15000}
    finally:
        await session.stop()


@pytest.mark.asyncio
async def test_marking_success_captures_even_a_background_click():
    """A slightly-missed 'mark success' click landing on <body> must still register --
    silently dropping it would save a flow with no success check at all."""
    session = RecordingSession("test-session-3", username="demo_user", password="demo_pass")
    await session.start()
    try:
        await session._page.goto(FIXTURE_PATH)
        await session._page.wait_for_timeout(50)

        session.mark_next_click_as_success()
        # click empty space below all elements -> hits <body>
        await session.dispatch_mouse(400, 400, "move")
        await session.dispatch_mouse(400, 400, "down")
        await session.dispatch_mouse(400, 400, "up")
        await session._page.wait_for_timeout(200)

        last = session.steps[-1]
        assert last["type"] == "wait_for_selector"
        assert last["selector"] in ("body", "html")
    finally:
        await session.stop()


@pytest.mark.asyncio
async def test_marking_assertion_captures_selector_and_given_value():
    session = RecordingSession("test-session-assert", username="demo_user", password="demo_pass")
    await session.start()
    try:
        await session._page.goto(FORM_LIST_PATH)
        await session._page.wait_for_timeout(50)

        session.mark_next_click_as_assertion("Order {{unique}}")
        await _click(session, "#latest")
        await session._page.wait_for_timeout(200)

        last = session.steps[-1]
        assert last == {"type": "assert_text_contains", "selector": "#latest", "value": "Order {{unique}}"}
    finally:
        await session.stop()


@pytest.mark.asyncio
async def test_assertion_marking_mode_clears_after_one_click():
    """A second, unrelated click after the assertion has been recorded should go back to
    being treated as a normal click step, not silently consume a stale pending value."""
    session = RecordingSession("test-session-assert-2", username="demo_user", password="demo_pass")
    await session.start()
    try:
        await session._page.goto(FORM_LIST_PATH)
        await session._page.wait_for_timeout(50)

        session.mark_next_click_as_assertion("Order {{unique}}")
        await _click(session, "#latest")
        await session._page.wait_for_timeout(100)

        await _click(session, "#latest")
        await session._page.wait_for_timeout(100)

        assert session.steps[-1] == {"type": "click", "selector": "#latest"}
    finally:
        await session.stop()


@pytest.mark.asyncio
async def test_background_click_ignored_outside_marking_mode():
    session = RecordingSession("test-session-4", username="demo_user", password="demo_pass")
    await session.start()
    try:
        await session._page.goto(FIXTURE_PATH)
        await session._page.wait_for_timeout(50)

        await session.dispatch_mouse(400, 400, "move")
        await session.dispatch_mouse(400, 400, "down")
        await session.dispatch_mouse(400, 400, "up")
        await session._page.wait_for_timeout(200)

        assert all(s["type"] != "click" for s in session.steps)
    finally:
        await session.stop()


@pytest.mark.asyncio
async def test_repeated_keystrokes_collapse_into_one_fill_step():
    session = RecordingSession("test-session-2", username="demo_user", password="demo_pass")
    await session.start()
    try:
        await session._page.goto(FIXTURE_PATH)
        await session._page.wait_for_timeout(50)

        await _click(session, "#username")
        for ch in "abc":
            await session.dispatch_text(ch)
            await session._page.wait_for_timeout(30)

        await session._page.wait_for_timeout(100)

        fill_steps = [s for s in session.steps if s["type"] == "fill"]
        assert len(fill_steps) == 1
        assert fill_steps[0]["value"] == "abc"
    finally:
        await session.stop()


@pytest.mark.asyncio
async def test_failed_initial_navigation_does_not_leak_the_browser():
    """A real site can be unreachable/slow (DNS failure, connection refused, timeout).
    Without cleanup, the already-launched browser process would be orphaned forever
    since create_session never returns a session_id for anything to reference it by."""
    before = len(recorder_manager._sessions)
    with pytest.raises(Exception):
        await recorder_manager.create_session(username="u", password="p", start_url="http://127.0.0.1:1/")
    assert len(recorder_manager._sessions) == before


@pytest.mark.asyncio
async def test_only_the_first_navigation_is_recorded():
    """Later navigations (SSO redirects, OAuth callbacks, form submissions) happen as a side
    effect of a click step and get replayed for free -- recording them as literal navigate
    steps would hardcode one-time-use tokens (OAuth `code`, `state`) that are already spent
    by the next run, breaking replay for exactly the SSO flows this tool exists to check."""
    session = RecordingSession("test-session-nav", username="demo_user", password="demo_pass")
    await session.start()
    try:
        await session.navigate(NAV_START_PATH)
        await session._page.wait_for_timeout(50)

        await _click(session, "#go")
        await session._page.wait_for_timeout(200)
        assert await session._page.locator("#landed").is_visible()

        navigate_steps = [s for s in session.steps if s["type"] == "navigate"]
        assert len(navigate_steps) == 1
        assert navigate_steps[0]["url"] == NAV_START_PATH

        click_steps = [s for s in session.steps if s["type"] == "click"]
        assert click_steps == [{"type": "click", "selector": "#go"}]
    finally:
        await session.stop()
