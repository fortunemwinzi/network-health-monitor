#!/usr/bin/env python3
"""Network Health Monitor v0.2
Ping + TCP port checks, CSV log, HTML report, and Telegram alerts
sent only when a device changes status."""

import csv
import html
import json
import os
import platform
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

DEVICES_FILE = Path("devices.json")
LOG_FILE = Path("logs/health_log.csv")
STATE_FILE = Path("logs/state.json")
REPORT_FILE = Path("reports/report.html")
TIMEOUT = 2  # seconds
COLOURS = {"UP": "#1e8e3e", "DEGRADED": "#e8a100", "DOWN": "#c8102e"}

PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Network Health Report</title>
<style>
body{font-family:Arial,sans-serif;margin:2rem;color:#222}
h1{color:#14284B;border-bottom:3px solid #C8102E;padding-bottom:.4rem}
table{border-collapse:collapse;width:100%;max-width:760px}
th{background:#14284B;color:#fff;text-align:left;padding:.5rem}
td{border-bottom:1px solid #ddd;padding:.5rem}
.meta{color:#555;margin-bottom:1rem}
</style></head><body>
<h1>Network Health Report</h1>
<p class="meta">Generated %%TIME%% | %%SUMMARY%%</p>
<table><tr><th>Device</th><th>Host</th><th>Status</th><th>Latency</th></tr>
%%ROWS%%</table></body></html>"""


def ping(host: str) -> bool:
    """Return True if the host answers one ping."""
    if platform.system() == "Windows":
        cmd = ["ping", "-n", "1", "-w", str(TIMEOUT * 1000), host]
    else:
        cmd = ["ping", "-c", "1", "-W", str(TIMEOUT), host]
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0


def check_port(host: str, port: int):
    """Return (is_open, response_time_ms) for a TCP connection test."""
    start = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=TIMEOUT):
            return True, round((time.perf_counter() - start) * 1000, 1)
    except OSError:
        return False, None


def check_device(device: dict) -> dict:
    ping_ok = ping(device["host"])
    port_ok, latency = (None, None)
    if "port" in device:
        port_ok, latency = check_port(device["host"], device["port"])
    if ping_ok and (port_ok is None or port_ok):
        status = "UP"
    elif ping_ok or port_ok:
        status = "DEGRADED"
    else:
        status = "DOWN"
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "name": device["name"],
        "host": device["host"],
        "ping": ping_ok,
        "port_open": port_ok,
        "latency_ms": latency,
        "status": status,
    }


def write_log(results: list) -> None:
    LOG_FILE.parent.mkdir(exist_ok=True)
    new_file = not LOG_FILE.exists()
    with LOG_FILE.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        if new_file:
            writer.writeheader()
        writer.writerows(results)


def write_html_report(results: list, summary: str) -> None:
    REPORT_FILE.parent.mkdir(exist_ok=True)
    rows = ""
    for r in results:
        lat = f"{r['latency_ms']} ms" if r["latency_ms"] else "-"
        colour = COLOURS[r["status"]]
        rows += (
            f"<tr><td>{html.escape(r['name'])}</td><td>{html.escape(r['host'])}</td>"
            f"<td style='color:{colour};font-weight:bold'>{r['status']}</td>"
            f"<td>{lat}</td></tr>\n"
        )
    page = (PAGE.replace("%%TIME%%", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                .replace("%%SUMMARY%%", summary)
                .replace("%%ROWS%%", rows))
    REPORT_FILE.write_text(page)


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(results: list) -> None:
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps({r["name"]: r["status"] for r in results}, indent=2))


def send_telegram(text: str) -> bool:
    """Send a Telegram message. Credentials come from environment variables."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Telegram not configured; skipping alert.")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    try:
        with urllib.request.urlopen(url, data=data, timeout=10) as resp:
            return resp.status == 200
    except OSError as exc:
        print(f"Telegram alert failed: {exc}")
        return False


def main() -> int:
    devices = json.loads(DEVICES_FILE.read_text())
    previous = load_state()
    results = [check_device(d) for d in devices]
    write_log(results)

    print(f"{'DEVICE':<26}{'HOST':<16}{'STATUS':<10}{'LATENCY'}")
    for r in results:
        lat = f"{r['latency_ms']} ms" if r["latency_ms"] else "-"
        print(f"{r['name']:<26}{r['host']:<16}{r['status']:<10}{lat}")

    counts = {s: sum(1 for r in results if r["status"] == s) for s in COLOURS}
    summary = f"{counts['UP']} up, {counts['DEGRADED']} degraded, {counts['DOWN']} down of {len(results)}"
    print(f"\n{summary}")
    write_html_report(results, summary)

    changes = [
        f"{r['name']}: {previous.get(r['name'], 'UP')} -> {r['status']}"
        for r in results
        if previous.get(r["name"], "UP") != r["status"]
    ]
    save_state(results)
    if changes:
        send_telegram("Network Health Alert\n" + "\n".join(changes))
    return 1 if counts["DOWN"] else 0


if __name__ == "__main__":
    sys.exit(main())