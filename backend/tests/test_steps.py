from unittest.mock import AsyncMock, MagicMock

import pytest

from app.checker.steps import execute_step


@pytest.mark.asyncio
async def test_navigate_success():
    page = AsyncMock()
    outcome = await execute_step(page, 0, {"type": "navigate", "url": "https://example.com"}, {})
    assert outcome.status == "success"
    page.goto.assert_awaited_once()


@pytest.mark.asyncio
async def test_fill_resolves_template_vars():
    page = AsyncMock()
    step = {"type": "fill", "selector": "#username", "value": "{{username}}"}
    outcome = await execute_step(page, 0, step, {"username": "demo1", "password": "secret"})
    assert outcome.status == "success"
    page.fill.assert_awaited_once_with("#username", "demo1", timeout=15000)


@pytest.mark.asyncio
async def test_step_failure_is_captured_not_raised():
    page = AsyncMock()
    page.click.side_effect = TimeoutError("timed out")
    outcome = await execute_step(page, 0, {"type": "click", "selector": "#missing"}, {})
    assert outcome.status == "fail"
    assert "timed out" in outcome.message


@pytest.mark.asyncio
async def test_assert_selector_absent_fails_when_visible():
    page = AsyncMock()
    nth_locator = MagicMock()
    nth_locator.is_visible = AsyncMock(return_value=True)
    locator = MagicMock()
    locator.count = AsyncMock(return_value=1)
    locator.nth = MagicMock(return_value=nth_locator)
    page.locator = MagicMock(return_value=locator)  # page.locator() is sync in real Playwright

    outcome = await execute_step(page, 0, {"type": "assert_selector_absent", "selector": ".error"}, {})
    assert outcome.status == "fail"


@pytest.mark.asyncio
async def test_unknown_step_type_fails():
    page = AsyncMock()
    outcome = await execute_step(page, 0, {"type": "not_a_real_step"}, {})
    assert outcome.status == "fail"
