import fnmatch
import logging
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

logger = logging.getLogger("issitelive.runner")


class WatchedFailure:
    def __init__(self, url: str, status: int):
        self.url = url
        self.status = status


def _matches_any(url: str, patterns: list[str]) -> bool:
    if not patterns:
        return False  # no patterns configured => watch nothing (opt-in, not opt-out)
    return any(fnmatch.fnmatch(url, p) for p in patterns)


async def run_check(db: Session, site: models.Site, account: models.Account, flow: models.Flow) -> models.CheckRun:
    started_at = datetime.utcnow()
    start_perf = time.perf_counter()

    # Written and committed immediately, before the browser even launches, so the run is
    # visible as "running" right away -- including across a page refresh, since this is now
    # the same row a client reads back rather than something that only appears once finished.
    check_run = models.CheckRun(
        site_id=site.id,
        account_id=account.id,
        status=models.RunStatus.running,
        started_at=started_at,
    )
    db.add(check_run)
    db.commit()
    db.refresh(check_run)

    watch_patterns = [w.get("pattern", "") for w in (flow.watch_patterns_json or [])]
    watched_failures: list[WatchedFailure] = []
    step_outcomes = []
    step_screenshots: dict[int, str] = {}
    overall_status = models.RunStatus.fail
    error_summary = None

    try:
        template_vars = {
            "username": account.username,
            "password": decrypt_password(account.encrypted_password),
        }

        os.makedirs(settings.screenshots_dir, exist_ok=True)
        run_stamp = int(started_at.timestamp())

        async def capture(idx: int, page) -> None:
            filename = f"{site.id}_{account.id}_{run_stamp}_{idx}.png"
            disk_path = os.path.join(settings.screenshots_dir, filename)
            try:
                await page.screenshot(path=disk_path, full_page=True)
                step_screenshots[idx] = f"/screenshots/{filename}"  # served via StaticFiles, see main.py
            except Exception:  # noqa: BLE001 - page may already be in a broken state; skip this step's screenshot
                pass

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
                await capture(idx, page)  # every step, not just failures -- lets you see what actually happened
                if outcome.status == "fail":
                    break  # stop the flow on first broken step; no point clicking further

            overall_status = models.RunStatus.success

            failed_step = next((o for o in step_outcomes if o.status == "fail"), None)
            if failed_step:
                overall_status = models.RunStatus.fail
                error_summary = f"Step {failed_step.step_index} ({failed_step.step_type}) failed: {failed_step.message}"
            elif watched_failures:
                overall_status = models.RunStatus.fail
                first = watched_failures[0]
                error_summary = f"AJAX call returned {first.status}: {first.url}"

            await browser.close()

    except Exception as exc:  # noqa: BLE001 - a crash must still resolve the run, not leave it stuck at "running"
        logger.exception("Check run crashed for site=%s account=%s", site.id, account.id)
        overall_status = models.RunStatus.fail
        error_summary = f"Check crashed: {exc}"

    last_step_screenshot = step_screenshots.get(len(step_outcomes) - 1) if step_outcomes else None
    duration_ms = int((time.perf_counter() - start_perf) * 1000)

    check_run.status = overall_status
    check_run.finished_at = datetime.utcnow()
    check_run.duration_ms = duration_ms
    check_run.error_summary = error_summary

    for outcome in step_outcomes:
        db.add(
            models.StepResult(
                check_run_id=check_run.id,
                step_index=outcome.step_index,
                step_type=outcome.step_type,
                status=models.RunStatus(outcome.status),
                message=outcome.message,
                screenshot_path=step_screenshots.get(outcome.step_index),
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
                # not a discrete step -- attach the page state as of the last real step instead
                screenshot_path=last_step_screenshot,
            )
        )

    db.commit()
    db.refresh(check_run)
    return check_run
