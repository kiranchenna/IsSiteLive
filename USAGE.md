# Using IsSiteLive: a worked example

This walks through setting up monitoring for a realistic scenario: a marketing site with a "Sign In" button that hands off to an SSO login, landing in an app that loads a shell first and then fetches its real data over AJAX. A plain uptime ping would miss both ways this can break — a login page rendering with a visible error despite a 200 response, and a post-login page that loads fine but whose data calls come back 500/502/504. This is exactly the case that motivated this tool.

We'll use a fictional site, `tinymedic.com`, as the example throughout.

## 1. Add the site

**Sites → + Add site**

| Field | Example value |
|---|---|
| Name | `TinyMedic` |
| Base URL | `https://tinymedic.com` |
| Check interval | `Every 5 min` |

Click **Create site**. You land on the site's detail page — everything else happens here.

## 2. Add a demo account

Real checks need a real login, so add a low-privilege account dedicated to monitoring (not a personal or admin account).

**Demo accounts → + Add account**

| Field | Example value |
|---|---|
| Label | `demo-readonly` |
| Username | `monitor@tinymedic.com` |
| Password | *(the account's real password)* |

You can add more than one account per site (e.g. `demo-admin` alongside `demo-readonly`) if different roles exercise different parts of the app — each gets checked independently, with its own pass/fail history.

## 3. Define the login flow

**Login flow → Steps (JSON)**

This is the sequence a headless browser runs on every check. Steps execute in order; the check stops and is marked failed at the first step that fails.

```json
[
  { "type": "navigate", "url": "https://tinymedic.com" },
  { "type": "click", "selector": "#sign-in" },
  { "type": "fill", "selector": "#username", "value": "{{username}}" },
  { "type": "fill", "selector": "#password", "value": "{{password}}" },
  { "type": "click", "selector": "#submit" },
  { "type": "wait_for_selector", "selector": "#app-dashboard", "timeout_ms": 15000 },
  { "type": "assert_selector_absent", "selector": ".error-banner" },
  { "type": "wait_for_load_state", "state": "networkidle", "timeout_ms": 15000 }
]
```

What each step type does:

| Step | Does |
|---|---|
| `navigate` | Loads a URL |
| `click` | Clicks an element by CSS selector |
| `fill` | Types into a field. Use `{{username}}` / `{{password}}` to substitute the account being checked — the same flow runs once per active account |
| `wait_for_selector` | Waits (up to `timeout_ms`) for an element to appear — this is how you confirm the post-login app actually loaded, not just that the login form submitted |
| `wait_for_url` | Waits for the URL to match a pattern, useful after an SSO redirect |
| `assert_selector_absent` | Fails the check if a matching element is visible — this is what catches "page loaded fine but shows an error message" |
| `wait_for_load_state` | Waits for the page to go network-idle (or another load state) |

Every step has a default 15s timeout, overridable per-step via `timeout_ms`.

**Why that last step matters:** the AJAX watcher below only catches calls that actually fire *before the browser closes*. The dashboard element appearing doesn't mean its data calls are done — they usually fire right after. Without a trailing `wait_for_load_state` (or another wait), the check can end before those calls complete and silently miss a 500. Always give the flow a moment to let background calls settle before it finishes.

**AJAX URL patterns to watch for 4xx/5xx responses**

```json
[
  { "pattern": "*/api/*" }
]
```

Independently of the steps above, the checker watches every network response the whole time the flow runs. Any response whose URL matches one of these glob patterns *and* returns a 4xx/5xx status fails the check — even if every step above passed and the page looked fine. This is what catches the "app loads, but its data calls 500" failure mode. Leave the list empty to watch every request on the page.

Click **Save flow**.

## 4. Set up alerts

**Alert channels** (top nav) → **+ Add channel**

Add a Slack webhook, mark it **default**:

| Field | Example value |
|---|---|
| Type | `Slack` |
| Label | `team-slack` |
| Webhook URL | `https://hooks.slack.com/services/…` |
| Default | ✓ |

Back on the TinyMedic site page, under **Alerts**, "Use default channels" is checked by default — meaning it'll notify `team-slack` without any extra setup. Uncheck it if this particular site should go to different channels instead (e.g. an `oncall-email` channel for a more critical property), or add site-specific channels alongside the defaults.

Alert behavior is fixed and intentionally simple:
- **Every failed run sends an alert** — no deduplication, so a flapping check pages every time
- **One recovery alert** fires on the transition from failing back to passing
- **Repeated successes stay silent** — no noise for the common case

## 5. Run it and read the results

Click **Run now** on the site page rather than waiting for the schedule, to confirm the flow actually works.

**Run history** shows each attempt. A failed run looks like:

```
● Aug 7, 10:14 AM   Step 1 (click) failed: Page.click: Timeout 15000ms exceeded.   29.9s
```

Click the row to expand it:

```
0  navigate
1  click    Page.click: Timeout 15000ms exceeded. waiting for locator("#sign-in")

View screenshot →
```

Each step's outcome is listed, and a full-page screenshot at the moment of failure is attached — this is usually enough to tell whether the site actually broke or a selector needs updating (e.g. the site redesigned its login button).

If a *watched* AJAX call is what failed the run (rather than a step), you'll see a `watched_response` row instead, with the offending status code and URL:

```
2  watched_response   HTTP 500   https://tinymedic.com/api/patients
```

## 6. Iterate on the flow

Login pages change. If a run starts failing because a selector no longer matches (rather than the site actually being down), update the **Steps (JSON)** on the site page and save — the next scheduled run (or another **Run now**) picks it up immediately, no restart needed.

## Dashboard

The **Dashboard** (top nav) shows every monitored site at a glance: a live pulse-line visual (steady beat = healthy, flatline = down), the current status, account count, and time since last check — the place to check first before drilling into any one site's history.
