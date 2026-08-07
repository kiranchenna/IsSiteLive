import fnmatch
import os
import time
from datetime import datetime

from playwright.async_api import async_playwright
from sqlalchemy.orm import Session

from app import models
from app.checker.steps import execute_step
from app.config import settings
from app.crypto import decrypt_password

RESPONSE_FAIL_THRESHOLD = 400


class WatchedFailure:
    def __init__(self, url: str, status: int):
        self.url = url
        self.status = status


def _matches_any(url: str, patterns: list[str]) -> bool:
    if not patterns:
        return True  # no patterns configured => watch everything
    return any(fnmatch.fnmatch(url, p) for p in patterns)


async def run_check(db: Session, site: models.Site, account: models.Account, flow: models.Flow) -> models.CheckRun:
    started_at = datetime.utcnow()
    start_perf = time.perf_counter()

    watch_patterns = [w.get("pattern", "") for w in (flow.watch_patterns_json or [])]
    watched_failures: list[WatchedFailure] = []
    step_outcomes = []
    screenshot_path = None

    template_vars = {
        "username": account.username,
        "password": decrypt_password(account.encrypted_password),
    }

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()

        def on_response(response):
            if response.status >= RESPONSE_FAIL_THRESHOLD and _matches_any(response.url, watch_patterns):
                watched_failures.append(WatchedFailure(response.url, response.status))

        page.on("response", on_response)

        for idx, step in enumerate(flow.steps_json or []):
            outcome = await execute_step(page, idx, step, template_vars)
            step_outcomes.append(outcome)
            if outcome.status == "fail":
                break  # stop the flow on first broken step; no point clicking further

        overall_status = models.RunStatus.success
        error_summary = None

        failed_step = next((o for o in step_outcomes if o.status == "fail"), None)
        if failed_step:
            overall_status = models.RunStatus.fail
            error_summary = f"Step {failed_step.step_index} ({failed_step.step_type}) failed: {failed_step.message}"
        elif watched_failures:
            overall_status = models.RunStatus.fail
            first = watched_failures[0]
            error_summary = f"AJAX call returned {first.status}: {first.url}"

        if overall_status == models.RunStatus.fail:
            os.makedirs(settings.screenshots_dir, exist_ok=True)
            filename = f"{site.id}_{account.id}_{int(started_at.timestamp())}.png"
            disk_path = os.path.join(settings.screenshots_dir, filename)
            try:
                await page.screenshot(path=disk_path, full_page=True)
                screenshot_path = f"/screenshots/{filename}"  # served via StaticFiles, see main.py
            except Exception:  # noqa: BLE001 - page may already be in a broken state; don't let this crash the run
                screenshot_path = None

        await browser.close()

    duration_ms = int((time.perf_counter() - start_perf) * 1000)

    check_run = models.CheckRun(
        site_id=site.id,
        account_id=account.id,
        status=overall_status,
        started_at=started_at,
        finished_at=datetime.utcnow(),
        duration_ms=duration_ms,
        error_summary=error_summary,
    )
    db.add(check_run)
    db.flush()  # get check_run.id before adding children

    for outcome in step_outcomes:
        db.add(
            models.StepResult(
                check_run_id=check_run.id,
                step_index=outcome.step_index,
                step_type=outcome.step_type,
                status=models.RunStatus(outcome.status),
                message=outcome.message,
                screenshot_path=screenshot_path if outcome.status == "fail" else None,
            )
        )

    for wf in watched_failures:
        db.add(
            models.StepResult(
                check_run_id=check_run.id,
                step_index=len(step_outcomes),
                step_type="watched_response",
                status=models.RunStatus.fail,
                http_status=wf.status,
                message=wf.url,
                screenshot_path=None,
            )
        )

    db.commit()
    db.refresh(check_run)
    return check_run
