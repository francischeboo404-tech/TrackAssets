#!/usr/bin/env python3
"""
TrackIT Deployment Rollback Script
===================================
Run this script when a deployment goes bad:
  - Checks the /health endpoint
  - Runs Alembic downgrade -1 (reverts the last migration)
  - Restarts the Gunicorn process

Usage:
    python scripts/rollback.py                    # auto-detect settings
    python scripts/rollback.py --steps 2          # roll back 2 migrations
    python scripts/rollback.py --health-url http://127.0.0.1:5000/health

Environment variables (override defaults):
    ROLLBACK_HEALTH_URL  - Full URL to /health endpoint
    ROLLBACK_STEPS       - Number of migration steps to undo (default: 1)
    GUNICORN_PID_FILE    - Path to gunicorn.pid file (default: gunicorn.pid)
"""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
import urllib.request
import urllib.error


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _health_check(url: str, timeout: int = 10) -> bool:
    """Return True if /health responds 200 with db:up."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            if resp.status != 200:
                return False
            import json
            body = json.loads(resp.read().decode())
            return body.get("status") == "ok" and body.get("database") == "up"
    except Exception as exc:
        print(f"  [HEALTH] Check failed: {exc}")
        return False


def _run(cmd: list[str], cwd: str | None = None) -> int:
    """Run a subprocess and stream its output. Returns exit code."""
    print(f"  [CMD] {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode


def _send_slack_alert(message: str) -> None:
    """Best-effort Slack alert for rollback events."""
    webhook = os.environ.get("SLACK_ALERT_WEBHOOK_URL")
    if not webhook:
        return
    import json
    payload = json.dumps({"text": f":warning: *TrackIT Rollback* — {message}"}).encode()
    try:
        req = urllib.request.Request(
            webhook,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main rollback procedure
# ---------------------------------------------------------------------------

def rollback(health_url: str, steps: int, gunicorn_pid_file: str) -> int:
    """
    Execute the rollback procedure.
    Returns 0 on success, non-zero on failure.
    """
    print("=" * 60)
    print("  TrackIT Deployment Rollback")
    print("=" * 60)
    _send_slack_alert("Rollback initiated — checking application health...")

    # Step 1: Check if the app is reachable (even if unhealthy — still rollback)
    print(f"\n[1/4] Health check: {health_url}")
    healthy = _health_check(health_url)
    if healthy:
        print("  Application is HEALTHY — rolling back migration anyway as requested.")
    else:
        print("  Application is UNHEALTHY — proceeding with rollback.")

    # Step 2: Run Alembic downgrade
    target = f"-{steps}"
    print(f"\n[2/4] Running Alembic downgrade ({steps} step{'s' if steps > 1 else ''})...")
    rc = _run(["python", "-m", "alembic", "downgrade", target])
    if rc != 0:
        msg = f"Alembic downgrade failed (exit code {rc})"
        print(f"  ERROR: {msg}")
        _send_slack_alert(f"Rollback FAILED — {msg}")
        return rc
    print("  Migration downgrade: OK")

    # Step 3: Restart Gunicorn (send SIGHUP = graceful reload)
    print(f"\n[3/4] Restarting Gunicorn (pid file: {gunicorn_pid_file})...")
    if os.path.exists(gunicorn_pid_file):
        try:
            with open(gunicorn_pid_file) as f:
                pid = int(f.read().strip())
            os.kill(pid, signal.SIGHUP)
            print(f"  Sent SIGHUP to Gunicorn PID {pid}")
            time.sleep(3)
        except Exception as exc:
            print(f"  WARNING: Could not reload Gunicorn: {exc}")
    else:
        print("  WARNING: gunicorn.pid not found — skipping process reload.")
        print("  Manually restart the application server.")

    # Step 4: Post-rollback health check
    print(f"\n[4/4] Post-rollback health check: {health_url}")
    time.sleep(5)
    healthy_after = _health_check(health_url)
    if healthy_after:
        msg = "Rollback COMPLETE — application is healthy."
        print(f"  SUCCESS: {msg}")
        _send_slack_alert(f":white_check_mark: {msg}")
        return 0
    else:
        msg = "Rollback done but application is STILL unhealthy — manual intervention required!"
        print(f"  WARNING: {msg}")
        _send_slack_alert(f":red_circle: {msg}")
        return 1


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TrackIT deployment rollback tool")
    parser.add_argument(
        "--health-url",
        default=os.environ.get("ROLLBACK_HEALTH_URL", "http://127.0.0.1:5000/health"),
        help="Full URL to the /health endpoint",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=int(os.environ.get("ROLLBACK_STEPS", "1")),
        help="Number of migration steps to roll back (default: 1)",
    )
    parser.add_argument(
        "--pid-file",
        default=os.environ.get("GUNICORN_PID_FILE", "gunicorn.pid"),
        help="Path to the Gunicorn PID file",
    )
    args = parser.parse_args()

    exit_code = rollback(
        health_url=args.health_url,
        steps=args.steps,
        gunicorn_pid_file=args.pid_file,
    )
    sys.exit(exit_code)
