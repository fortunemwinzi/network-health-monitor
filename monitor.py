#!/usr/bin/env python3
"""Network Health Monitor v0.1
Checks each device with ping and an optional TCP port test,
prints a summary and appends results to a CSV log."""

import csv
import json
import platform
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

DEVICES_FILE = Path("devices.json")
LOG_FILE = Path("logs/health_log.csv")
TIMEOUT = 2  # seconds


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


def main() -> int:
    devices = json.loads(DEVICES_FILE.read_text())
    results = [check_device(d) for d in devices]
    write_log(results)

    print(f"{'DEVICE':<26}{'HOST':<16}{'STATUS':<8}{'LATENCY'}")
    for r in results:
        lat = f"{r['latency_ms']} ms" if r["latency_ms"] else "-"
        print(f"{r['name']:<26}{r['host']:<16}{r['status']:<8}{lat}")

    down = [r for r in results if r["status"] == "DOWN"]
    print(f"\n{len(results) - len(down)}/{len(results)} devices up")
    return 1 if down else 0


if __name__ == "__main__":
    sys.exit(main())