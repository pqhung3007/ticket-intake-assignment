"""Seed a running local instance with realistic demo tickets, through the real HTTP API.

Requires the backend to run with AUTH_MODE=dev (the docker compose default).
Uses only the standard library and runs on Python 3.8+, so it works from the host as is:

    python3 backend/scripts/seed_demo.py                 # against http://localhost:8000
    python3 backend/scripts/seed_demo.py http://host:port

Safe to re-run: every report carries a request_key, so a second run files nothing new and
skips the follow-up activity (triage, comments) for reports that already existed.
"""

# Keeps the type hints lazy so the script runs on older system Pythons (macOS ships 3.9).
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

_root = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
if not _root.startswith(("http://", "https://")):
    raise SystemExit(f"Base URL must start with http:// or https:// (got {_root!r})")
BASE = _root + "/api/v1"
AGENT = "bug-intake"

# Talk to the local server directly. urllib otherwise honours system/VPN proxy settings
# (on macOS even ones not exported as env vars), which can stall requests to localhost.
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class Unreachable(Exception):
    pass


def call(method: str, path: str, user: str, body: dict[str, Any] | None = None) -> tuple[int, Any]:
    req = urllib.request.Request(  # noqa: S310 (scheme validated above)
        BASE + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer dev:{user}", "Content-Type": "application/json"},
    )
    try:
        with _opener.open(req, timeout=5) as res:
            return res.status, json.load(res)
    except urllib.error.HTTPError as err:
        raw = err.read()
        try:
            return err.code, json.loads(raw or b"{}")
        except ValueError:
            return err.code, raw.decode(errors="replace")[:200]
    except (urllib.error.URLError, OSError) as err:  # refused, DNS, timeout
        raise Unreachable(f"{method} {BASE + path}: {getattr(err, 'reason', err)}") from err


@dataclass
class Step:
    """A follow-up action on a ticket: ('patch', user, fields) or ('comment', user, text)."""

    kind: str
    user: str
    payload: Any


@dataclass
class Report:
    key: str
    reporter: str  # dev user; "<user>:agent:<id>" files it as that user's agent
    body: dict[str, Any]
    steps: list[Step] = field(default_factory=list)


def via_agent(user: str) -> str:
    return f"{user}:agent:{AGENT}"


REPORTS: list[Report] = [
    Report(
        "demo-export-timeout",
        via_agent("alice"),
        {
            "title": "CSV export times out for 12-month reports",
            "target_app": "reports",
            "severity": "high",
            "description": 'Reported in #support: "the export is broken again". Large date ranges fail since '
            "Monday; ranges under 3 months still work. Affects the finance team's month-end close.",
            "steps_to_reproduce": "1. Open Reports\n2. Choose 'Last 12 months'\n3. Click Export → CSV",
            "expected_behavior": "The CSV downloads within a few seconds",
            "actual_behavior": "Spinner for ~60s, then a 504 Gateway Timeout",
            "environment": "Chrome 141, macOS 15",
        },
        [
            Step(
                "patch", "tara", {"assignee_id": "dev-tara", "status": "in_progress", "severity": "critical"}
            ),
            Step("comment", "bob", "Same on the Q3 board report. Small ranges are fine."),
            Step(
                "comment",
                "tara",
                "Export query does a full scan on events since the Monday migration. "
                "Adding the missing index; raising to critical because month-end is blocked.",
            ),
        ],
    ),
    Report(
        "demo-shared-links-leak",
        "alice",
        {
            "title": "Shared dashboard links expose other workspaces' data",
            "target_app": "dashboards",
            "severity": "critical",
            "confidential": True,
            "description": "Changing the numeric id in a public share link opens a dashboard from a "
            "different workspace without signing in.",
            "steps_to_reproduce": "1. Share any dashboard publicly\n2. Open the link\n"
            "3. Change /share/1042 to /share/1041",
            "expected_behavior": "404, or a sign-in prompt",
            "actual_behavior": "Another workspace's dashboard renders with live data",
        },
        [
            Step("patch", "tara", {"assignee_id": "dev-tara", "status": "in_progress"}),
            Step(
                "comment",
                "tara",
                "Public share links disabled behind a flag while we move to unguessable "
                "tokens. Keeping this confidential until the fix ships.",
            ),
        ],
    ),
    Report(
        "demo-calendar-duplicates",
        via_agent("bob"),
        {
            "title": "Calendar sync duplicates recurring events",
            "target_app": "calendar",
            "severity": "high",
            "description": "Weekly recurring meetings show up twice after the nightly Google Calendar sync. "
            "One-off events are fine.",
            "steps_to_reproduce": "1. Connect Google Calendar\n2. Create a weekly recurring event\n"
            "3. Wait for the nightly sync",
            "expected_behavior": "One entry per occurrence",
            "actual_behavior": "Two entries per occurrence; deleting one deletes both",
        },
    ),
    Report(
        "demo-password-reset",
        "bob",
        {
            "title": "Password reset link expires immediately",
            "target_app": "auth",
            "severity": "critical",
            "description": "Users clicking the reset link straight from the email get 'link expired'. "
            "Support has 14 tickets about it today.",
            "actual_behavior": "'This link has expired' on first click",
            "environment": "All browsers; started after the 2.31 deploy",
        },
        [Step("patch", "adam", {"assignee_id": "dev-tara", "status": "in_progress"})],
    ),
    Report(
        "demo-invoice-currency",
        "bob",
        {
            "title": "Invoice PDF shows wrong currency symbol",
            "target_app": "billing",
            "severity": "high",
            "description": "EUR invoices render with a $ sign. Totals are correct, only the symbol is wrong.",
            "expected_behavior": "€1,250.00",
            "actual_behavior": "$1,250.00",
        },
    ),
    Report(
        "demo-slack-delay",
        via_agent("tara"),
        {
            "title": "Slack notifications delayed by 10+ minutes",
            "target_app": "notifications",
            "severity": "medium",
            "description": "Mentions reach Slack 10-15 minutes late during business hours; "
            "email notifications are on time.",
        },
    ),
    Report(
        "demo-search-accents",
        "tara",
        {
            "title": "Search ignores accented characters",
            "target_app": "search",
            "severity": "medium",
            "description": "Searching 'resume' doesn't find 'résumé' and vice versa.",
        },
        [
            Step("patch", "tara", {"status": "in_progress"}),
            Step("patch", "tara", {"status": "resolved"}),
            Step("comment", "tara", "Fixed by switching the search column to an unaccented collation."),
        ],
    ),
    Report(
        "demo-dark-tooltips",
        "alice",
        {
            "title": "Chart tooltips unreadable in dark mode",
            "target_app": "dashboards",
            "severity": "low",
            "description": "Tooltip text is dark grey on a black background.",
            "environment": "Firefox 140, Windows 11",
        },
        [
            Step("patch", "tara", {"status": "resolved"}),
            Step("comment", "alice", "Still happening in Firefox, reopening."),
            Step("patch", "alice", {"status": "open"}),
        ],
    ),
    Report(
        "demo-import-emoji",
        "alice",
        {
            "title": "Bulk import silently skips rows containing emoji",
            "target_app": "imports",
            "severity": "medium",
            "description": "Importing a 2,000-row CSV reports success, but rows with emoji in any "
            "column are missing and no error is shown.",
            "steps_to_reproduce": "1. Settings → Import\n2. Upload a CSV where one row's name is 'Café ☕'\n"
            "3. Check the imported records",
            "expected_behavior": "All rows imported, or a clear error listing the skipped rows",
            "actual_behavior": "'Import complete: 2,000 rows' but only 1,987 exist",
        },
    ),
    Report(
        "demo-login-safari",
        "bob",
        {
            "title": "Login button misaligned on mobile Safari",
            "target_app": "auth",
            "severity": "low",
            "description": "On iPhone SE the Sign in button overlaps the footer links.",
            "environment": "iOS 18, Safari",
        },
        [
            Step("patch", "bob", {"status": "closed"}),
            Step("comment", "bob", "Duplicate of an older report, closing."),
        ],
    ),
]


def main() -> int:
    print(f"Seeding demo tickets into {BASE} ...", flush=True)
    status, me = call("GET", "/me", "alice")
    if status != 200:
        print(f"The API answered HTTP {status} for a dev user: {me}")
        print("Is the backend running with AUTH_MODE=dev (the docker compose default)?")
        return 1

    # Users exist in the app once they've used it; needed for assignment.
    for user in ("alice", "bob", "tara", "adam"):
        call("GET", "/me", user)

    created = skipped = 0
    for report in REPORTS:
        status, res = call("POST", "/tickets", report.reporter, {**report.body, "request_key": report.key})
        if status not in (200, 201):
            print(f"  ! {report.body['title']}: HTTP {status} {res}")
            continue
        ticket = res["ticket"]
        if not res["created"]:
            skipped += 1
            print(f"  = #{ticket['number']:<3} already exists: {ticket['title']}")
            continue
        created += 1
        version = ticket["version"]
        for step in report.steps:
            path = f"/tickets/{ticket['number']}"
            if step.kind == "patch":
                status, res = call("PATCH", path, step.user, {"version": version, **step.payload})
                if status == 200:
                    version = res["version"]
            else:
                status, res = call("POST", f"{path}/comments", step.user, {"body": step.payload})
            if status not in (200, 201):
                print(f"    ! {step.kind} by {step.user}: HTTP {status} {res}")
        who = f"{report.reporter.split(':')[0]}{' via agent' if ':agent:' in report.reporter else ''}"
        print(f"  + #{ticket['number']:<3} {ticket['title']}  ({who})", flush=True)

    print(f"\nDone: {created} created, {skipped} already existed. Open http://localhost:5173")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Unreachable as exc:
        print(f"Cannot reach the API: {exc}")
        print("Is the stack running? Check with: docker compose ps")
        raise SystemExit(1) from None
    except KeyboardInterrupt:
        raise SystemExit(130) from None
