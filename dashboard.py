#!/usr/bin/env python3
"""
dashboard.py — Flask web server for TOR IP Rotator
Serves the live dashboard and SSE event stream.
"""

import json
import time
import queue
import threading
from pathlib import Path
from flask import Flask, Response, render_template, jsonify, request, stream_with_context
import tor_rotator

app = Flask(__name__)
LOG_FILE = Path("logs/ip.txt")


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    return jsonify(tor_rotator.status())


@app.route("/api/start", methods=["POST"])
def api_start():
    tor_rotator.start()
    return jsonify({"ok": True, "message": "Rotator started"})


@app.route("/api/stop", methods=["POST"])
def api_stop():
    tor_rotator.stop()
    return jsonify({"ok": True, "message": "Rotator stopped"})


@app.route("/api/logs")
def api_logs():
    """Return last N log lines from ip.txt."""
    limit = int(request.args.get("limit", 200))
    if not LOG_FILE.exists():
        return jsonify([])
    lines = LOG_FILE.read_text().strip().splitlines()
    records = []
    for line in lines[-limit:]:
        try:
            records.append(json.loads(line))
        except Exception:
            pass
    return jsonify(records[::-1])   # newest first


@app.route("/api/logs/raw")
def api_logs_raw():
    """Return raw ip.txt content."""
    if not LOG_FILE.exists():
        return Response("No logs yet.", mimetype="text/plain")
    return Response(LOG_FILE.read_text(), mimetype="text/plain")


@app.route("/stream")
def stream():
    """Server-Sent Events endpoint — pushes new log records in real time."""
    def event_generator():
        # Send a heartbeat first so the browser opens the connection
        yield "data: {\"type\":\"connected\"}\n\n"
        # Create a per-client queue
        client_q: queue.Queue = queue.Queue()

        # Relay thread: moves events from the global queue to this client
        def relay():
            while True:
                try:
                    item = tor_rotator.EVENT_QUEUE.get(timeout=30)
                    client_q.put(item)
                    tor_rotator.EVENT_QUEUE.task_done()
                except queue.Empty:
                    client_q.put({"type": "heartbeat"})

        t = threading.Thread(target=relay, daemon=True)
        t.start()

        while True:
            try:
                event = client_q.get(timeout=30)
                yield f"data: {json.dumps(event)}\n\n"
            except queue.Empty:
                yield "data: {\"type\":\"heartbeat\"}\n\n"

    return Response(
        stream_with_context(event_generator()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════╗
║   TOR IP ROTATOR  —  Dashboard v1.0          ║
║   http://127.0.0.1:5000                      ║
╚══════════════════════════════════════════════╝
""")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
