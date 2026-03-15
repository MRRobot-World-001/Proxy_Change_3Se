#!/usr/bin/env python3
"""
tor_rotator.py — TOR IP Rotator for Kali Linux
Rotates Tor exit nodes every N seconds across countries.
Logs each IP to logs/ip.txt and exposes events via Flask-SSE.
"""

import os
import sys
import time
import json
import queue
import socket
import threading
import datetime
import requests
import subprocess
from pathlib import Path

# ── Tor / Stem ─────────────────────────────────────────────────────────────
try:
    from stem import Signal
    from stem.control import Controller
    import stem.process
except ImportError:
    print("[!] stem not installed. Run: pip install stem")
    sys.exit(1)

# ── Config ──────────────────────────────────────────────────────────────────
TOR_CONTROL_PORT  = 9051
TOR_SOCKS_PORT    = 9050
TOR_PASSWORD      = "torpassword"          # must match HashedControlPassword in torrc
ROTATE_INTERVAL   = 3                      # seconds between rotations
LOG_FILE          = Path("logs/ip.txt")
EVENT_QUEUE: queue.Queue = queue.Queue()   # shared SSE event bus

# Country exit-node hints (ISO-3166-1 alpha-2)
COUNTRIES = [
    "us", "de", "fr", "nl", "gb", "ch", "se", "no", "ca",
    "jp", "au", "br", "sg", "in", "ru", "pl", "it", "es",
    "at", "be", "cz", "dk", "fi", "gr", "hu", "ie", "kr",
    "mx", "nz", "pt", "ro", "za", "ar", "cl", "co", "eg",
    "id", "my", "ph", "th", "tr", "ua", "vn"
]

_country_index = 0
_running = False
_lock = threading.Lock()


# ── Helpers ─────────────────────────────────────────────────────────────────

def log_event(level: str, message: str, extra: dict | None = None):
    """Write to console, log file, and push to SSE queue."""
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    record = {
        "timestamp": ts,
        "level": level.upper(),
        "message": message,
        **(extra or {})
    }
    # Console
    color = {"INFO": "\033[92m", "WARN": "\033[93m", "ERROR": "\033[91m"}.get(level.upper(), "\033[0m")
    print(f"{color}[{ts}] [{level.upper()}] {message}\033[0m")

    # File
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a") as f:
        f.write(json.dumps(record) + "\n")

    # SSE queue
    EVENT_QUEUE.put(record)


def get_tor_ip() -> dict:
    """Query current exit-node IP through the Tor SOCKS proxy."""
    proxies = {
        "http":  f"socks5h://127.0.0.1:{TOR_SOCKS_PORT}",
        "https": f"socks5h://127.0.0.1:{TOR_SOCKS_PORT}",
    }
    try:
        r = requests.get(
            "https://ipinfo.io/json",
            proxies=proxies,
            timeout=10,
        )
        data = r.json()
        return {
            "ip":      data.get("ip",      "unknown"),
            "city":    data.get("city",    "unknown"),
            "region":  data.get("region",  "unknown"),
            "country": data.get("country", "??"),
            "org":     data.get("org",     "unknown"),
            "timezone":data.get("timezone","unknown"),
        }
    except Exception as exc:
        return {"ip": "error", "city": "-", "region": "-",
                "country": "??", "org": str(exc), "timezone": "-"}


def new_circuit(controller, country_code: str) -> bool:
    """Request a new Tor circuit, optionally biasing to a country."""
    try:
        # Set ExitNodes hint
        controller.set_conf("ExitNodes", f"{{{country_code}}}")
        controller.signal(Signal.NEWNYM)
        time.sleep(1)          # let Tor build the circuit
        return True
    except Exception as exc:
        log_event("ERROR", f"Circuit change failed: {exc}")
        return False


def is_tor_running() -> bool:
    """Check if Tor control port is reachable."""
    try:
        s = socket.create_connection(("127.0.0.1", TOR_CONTROL_PORT), timeout=2)
        s.close()
        return True
    except OSError:
        return False


def ensure_tor_config():
    """Append required lines to /etc/tor/torrc if missing."""
    torrc = Path("/etc/tor/torrc")
    if not torrc.exists():
        log_event("WARN", "torrc not found at /etc/tor/torrc")
        return
    text = torrc.read_text()
    lines_needed = {
        "ControlPort 9051": "ControlPort 9051\n",
        "HashedControlPassword": None,  # skip — user must set own password
        "CookieAuthentication": "CookieAuthentication 1\n",
        "SocksPort 9050": "SocksPort 9050\n",
    }
    additions = []
    for key, line in lines_needed.items():
        if line and key not in text:
            additions.append(line)
    if additions:
        try:
            with torrc.open("a") as f:
                f.writelines(additions)
            log_event("INFO", "torrc updated — restart Tor for changes to take effect.")
        except PermissionError:
            log_event("WARN", "Cannot write torrc (need root). Add manually:\n" +
                      "  ControlPort 9051\n  CookieAuthentication 1")


# ── Rotation loop ────────────────────────────────────────────────────────────

def rotation_loop():
    global _running, _country_index

    if not is_tor_running():
        log_event("ERROR", "Tor control port not reachable. Start Tor first: sudo service tor start")
        return

    log_event("INFO", "Connecting to Tor control port…")

    try:
        with Controller.from_port(port=TOR_CONTROL_PORT) as ctrl:
            try:
                ctrl.authenticate(password=TOR_PASSWORD)
                log_event("INFO", "Authenticated with Tor controller (password)")
            except Exception:
                try:
                    ctrl.authenticate()   # cookie auth
                    log_event("INFO", "Authenticated with Tor controller (cookie)")
                except Exception as e:
                    log_event("ERROR", f"Tor auth failed: {e}")
                    return

            log_event("INFO", f"Rotation started — interval {ROTATE_INTERVAL}s over {len(COUNTRIES)} countries")

            while _running:
                with _lock:
                    country = COUNTRIES[_country_index % len(COUNTRIES)]
                    _country_index += 1

                ok = new_circuit(ctrl, country)
                if ok:
                    info = get_tor_ip()
                    log_event("INFO",
                        f"New IP: {info['ip']} | {info['city']}, {info['country']} | {info['org']}",
                        {"ip_info": info, "target_country": country}
                    )
                else:
                    log_event("WARN", f"Failed to get circuit via [{country.upper()}]")

                time.sleep(ROTATE_INTERVAL)

    except Exception as exc:
        log_event("ERROR", f"Controller error: {exc}")
    finally:
        _running = False
        log_event("INFO", "Rotation stopped.")


# ── Public API ───────────────────────────────────────────────────────────────

def start():
    global _running
    if _running:
        log_event("WARN", "Already running.")
        return
    _running = True
    t = threading.Thread(target=rotation_loop, daemon=True, name="rotator")
    t.start()
    log_event("INFO", "Rotator thread started.")


def stop():
    global _running
    _running = False
    log_event("INFO", "Stop signal sent.")


def status() -> dict:
    return {
        "running": _running,
        "country_index": _country_index,
        "current_country": COUNTRIES[(_country_index - 1) % len(COUNTRIES)] if _country_index else "none",
        "interval": ROTATE_INTERVAL,
        "total_rotations": _country_index,
    }


# ── Standalone entry ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    ensure_tor_config()
    start()
    try:
        while _running:
            time.sleep(1)
    except KeyboardInterrupt:
        stop()
        print("\n[!] Stopped.")
