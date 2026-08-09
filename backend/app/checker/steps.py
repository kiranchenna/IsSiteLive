"""Step executors for a single check run.

Each step is a dict from Flow.steps_json, e.g.:
  {"type": "navigate", "url": "https://example.com"}
  {"type": "click", "selector": "#sign-in"}
  {"type": "fill", "selector": "#username", "value": "{{username}}"}
  {"type": "wait_for_selector", "selector": "#dashboard", "timeout_ms": 15000}
  {"type": "wait_for_url", "pattern": "**/app/**", "timeout_ms": 15000}
  {"type": "assert_selector_absent", "selector": ".error-banner"}
  {"type": "assert_text_contains", "selector": "#latest-entry", "value": "Order {{unique}}"}
  {"type": "wait_for_load_state", "state": "networkidle", "timeout_ms": 15000}

`{{unique}}` is a built-in template var (alongside `{{username}}`/`{{password}}`) that the
runner generates fresh once per run -- fill a form field with a value containing it, then
assert_text_contains for that same value on whatever page displays what got saved. This is
what makes a "did my form submission actually save?" flow meaningful on a repeating schedule:
without a unique value each run, the assertion could pass by matching a leftover from a
previous run even if this run's submission silently failed.
"""
from dataclasses import dataclass
from typing import Any, Optional

from playwright.async_api import Page

from app.config import settings


@dataclass
class StepOutcome:
    step_index: int
    step_type: str
    status: str  # "success" | "fail"
    message: Optional[str] = None


def _resolve_template(value: str, template_vars: dict[str, str]) -> str:
    for key, val in template_vars.items():
        value = value.replace(f"{{{{{key}}}}}", val)
    return value


async def execute_step(
    page: Page, step_index: int, step: dict[str, Any], template_vars: dict[str, str]
) -> StepOutcome:
    step_type = step.get("type")
    timeout_ms = step.get("timeout_ms", settings.default_step_timeout_ms)

    try:
        if step_type == "navigate":
            # domcontentloaded rather than the default "load": real sites keep the load event
            # pending on slow-loading trackers/analytics long after the page is actually
            # usable, which would otherwise time out checks on pages that are genuinely fine.
            await page.goto(step["url"], wait_until="domcontentloaded", timeout=timeout_ms)

        elif step_type == "click":
            await page.click(step["selector"], timeout=timeout_ms)

        elif step_type == "fill":
            value = _resolve_template(step["value"], template_vars)
            await page.fill(step["selector"], value, timeout=timeout_ms)

        elif step_type == "wait_for_selector":
            await page.wait_for_selector(step["selector"], timeout=timeout_ms)

        elif step_type == "wait_for_url":
            await page.wait_for_url(step["pattern"], timeout=timeout_ms)

        elif step_type == "wait_for_load_state":
            await page.wait_for_load_state(step.get("state", "networkidle"), timeout=timeout_ms)

        elif step_type == "assert_selector_absent":
            selector = step["selector"]
            locator = page.locator(selector)
            count = await locator.count()
            visible_count = 0
            for i in range(count):
                if await locator.nth(i).is_visible():
                    visible_count += 1
            if visible_count > 0:
                return StepOutcome(step_index, step_type, "fail", f"Found {visible_count} visible match(es) for {selector!r}")

        elif step_type == "assert_text_contains":
            selector = step["selector"]
            expected = _resolve_template(step["value"], template_vars)
            await page.wait_for_selector(selector, timeout=timeout_ms)
            actual = await page.locator(selector).first.text_content() or ""
            if expected not in actual:
                return StepOutcome(
                    step_index, step_type, "fail", f"Expected {selector!r} to contain {expected!r}, but got {actual!r}"
                )

        else:
            return StepOutcome(step_index, step_type or "unknown", "fail", f"Unknown step type: {step_type!r}")

        return StepOutcome(step_index, step_type, "success")

    except Exception as exc:  # noqa: BLE001 - any Playwright/timeout error should fail the step, not crash the run
        return StepOutcome(step_index, step_type or "unknown", "fail", str(exc))
