#!/usr/bin/env python3
"""Local web UI for the message exporter.

Runs only on 127.0.0.1 with a per-launch URL token; serves no external
assets and makes no network calls. Start it with run.command (macOS).
"""
from __future__ import annotations

import secrets
import socket
import threading
import webbrowser
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from subprocess import run as run_cmd
import sys

from flask import (Flask, abort, jsonify, redirect, render_template,
                   request, url_for)

from exporter.backup.decrypt import WrongPasswordError
from exporter.backup.device import (DeviceError, list_devices,
                                    tools_available)
from exporter.backup.locate import (FullDiskAccessError, list_backups,
                                    read_backup_info)
from exporter.pipeline import run_export_from_backup, run_export_from_device

app = Flask(__name__)
TOKEN = secrets.token_urlsafe(16)


@dataclass
class JobStatus:
    running: bool = False
    done: bool = False
    error: str | None = None
    stage: str = ""
    percent: float = 0.0
    out_dir: str = ""
    outputs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    conversation_count: int = 0
    message_count: int = 0


JOB = JobStatus()
JOB_LOCK = threading.Lock()


def require_token(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if request.args.get("t") != TOKEN and request.form.get("t") != TOKEN:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


@app.route("/")
@require_token
def index():
    try:
        backups = list_backups()
        fda_blocked = False
    except FullDiskAccessError:
        backups = []
        fda_blocked = True
    return render_template("index.html", token=TOKEN, backups=backups,
                           fda_blocked=fda_blocked, is_mac=sys.platform == "darwin",
                           have_device_tools=tools_available(),
                           devices=_connected_devices())


def _connected_devices():
    """Connected iPhones, or [] if the tools aren't installed / none plugged in."""
    if not tools_available():
        return []
    try:
        return list_devices()
    except DeviceError:
        return []


@app.route("/start", methods=["POST"])
@require_token
def start():
    global JOB
    with JOB_LOCK:
        if JOB.running:
            return redirect(url_for("progress_page", t=TOKEN))
        backup_path = Path(request.form["backup_path"]).expanduser()
        password = request.form.get("password") or None

        info = read_backup_info(backup_path)
        if info is None:
            return render_template("index.html", token=TOKEN, backups=[],
                                   fda_blocked=False, is_mac=sys.platform == "darwin",
                                   error=f"That folder doesn't look like an iPhone "
                                         f"backup: {backup_path}")
        if info.encrypted and not password:
            return render_template("password.html", token=TOKEN,
                                   backup=info, error=None)

        JOB = JobStatus(running=True, stage="Starting…")
        thread = threading.Thread(target=_run_job,
                                  args=(backup_path, password), daemon=True)
        thread.start()
    return redirect(url_for("progress_page", t=TOKEN))


@app.route("/start-device", methods=["POST"])
@require_token
def start_device():
    global JOB
    with JOB_LOCK:
        if JOB.running:
            return redirect(url_for("progress_page", t=TOKEN))
        udid = request.form.get("udid", "").strip()
        password = request.form.get("password") or None
        discard = request.form.get("discard_backup") == "on"
        if not udid:
            return redirect(url_for("index", t=TOKEN))
        JOB = JobStatus(running=True, stage="Starting backup…")
        thread = threading.Thread(
            target=_run_export, kwargs={
                "fn": lambda progress: run_export_from_device(
                    udid, password=password, discard_backup=discard,
                    progress=progress),
            }, daemon=True)
        thread.start()
    return redirect(url_for("progress_page", t=TOKEN))


def _run_job(backup_path: Path, password: str | None) -> None:
    _run_export(fn=lambda progress: run_export_from_backup(
        backup_path, password, progress=progress))


def _run_export(fn) -> None:
    def progress(detail: str, pct: float) -> None:
        JOB.stage = detail
        JOB.percent = max(JOB.percent, round(pct * 100, 1))

    try:
        result = fn(progress)
        JOB.out_dir = str(result.out_dir)
        JOB.outputs = [str(p) for p in result.outputs]
        JOB.warnings = result.warnings
        JOB.conversation_count = result.conversation_count
        JOB.message_count = result.message_count
        JOB.done = True
        JOB.percent = 100.0
    except WrongPasswordError as exc:
        JOB.error = str(exc)
    except DeviceError as exc:
        JOB.error = str(exc)
    except FullDiskAccessError:
        JOB.error = ("macOS blocked access to the backup. Give Terminal "
                     "Full Disk Access in System Settings → Privacy & "
                     "Security, then try again.")
    except Exception as exc:
        JOB.error = f"Export failed: {exc}"
    finally:
        JOB.running = False


@app.route("/progress")
@require_token
def progress_page():
    return render_template("progress.html", token=TOKEN)


@app.route("/status")
@require_token
def status():
    return jsonify({
        "running": JOB.running, "done": JOB.done, "error": JOB.error,
        "stage": JOB.stage, "percent": JOB.percent,
    })


@app.route("/done")
@require_token
def done():
    return render_template("done.html", token=TOKEN, job=JOB)


@app.route("/open-folder", methods=["POST"])
@require_token
def open_folder():
    if JOB.out_dir and sys.platform == "darwin":
        run_cmd(["open", JOB.out_dir], check=False)
    return redirect(url_for("done", t=TOKEN))


def main() -> None:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    url = f"http://127.0.0.1:{port}/?t={TOKEN}"
    print(f"\n  Message Exporter is running.\n  Open this link if your "
          f"browser doesn't open automatically:\n\n    {url}\n\n"
          f"  Keep this window open while exporting. Press Ctrl+C to quit.\n")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    main()
