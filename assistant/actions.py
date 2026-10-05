"""Constrained Windows actions exposed to Needle; no arbitrary command execution."""
from __future__ import annotations

import csv
import io
import os
from pathlib import Path
import shutil
import subprocess
import threading
from datetime import datetime
from typing import Annotated

import needle

MAX_TIMER_SECONDS = 24 * 60 * 60

_ALIASES = {
    "calculator": "calculator", "calc": "calculator", "notepad": "notepad",
    "chrome": "chrome", "google chrome": "chrome", "browser": "chrome",
    "explorer": "explorer", "file explorer": "explorer", "terminal": "terminal", "windows terminal": "terminal",
    "paint": "paint", "snipping tool": "snipping", "snipping": "snipping", "vs code": "vscode", "visual studio code": "vscode", "code": "vscode",
    "settings": "settings", "system settings": "settings", "task manager": "taskmanager", "taskmgr": "taskmanager",
    "clock": "clock", "sound settings": "sound", "wifi settings": "network", "wi-fi settings": "network",
    "network settings": "network", "bluetooth settings": "bluetooth", "display settings": "display",
}
_COMMANDS = {"calculator": ["calc.exe"], "notepad": ["notepad.exe"], "explorer": ["explorer.exe"], "terminal": ["wt.exe"], "paint": ["mspaint.exe"], "snipping": ["SnippingTool.exe"], "taskmanager": ["taskmgr.exe"]}
_URIS = {"settings": "ms-settings:", "clock": "ms-clock:", "sound": "ms-settings:sound", "network": "ms-settings:network-wifi", "bluetooth": "ms-settings:bluetooth", "display": "ms-settings:display"}
_PROCESS_NAMES = {"calculator": {"calculator.exe", "calc.exe"}, "notepad": {"notepad.exe"}, "chrome": {"chrome.exe"}, "explorer": {"explorer.exe"}, "terminal": {"windowsterminal.exe", "wt.exe"}, "paint": {"mspaint.exe"}, "snipping": {"snippingtool.exe"}, "vscode": {"code.exe"}, "taskmanager": {"taskmgr.exe"}, "clock": {"time.exe", "clock.exe"}}
_BACKGROUND = {"system", "registry", "smss.exe", "csrss.exe", "wininit.exe", "services.exe", "lsass.exe", "svchost.exe", "dwm.exe", "fontdrvhost.exe", "conhost.exe"}

def _canonical(app_name: str) -> str:
    name = " ".join(app_name.strip().lower().split())
    if name not in _ALIASES:
        raise ValueError(f"'{app_name}' is not an approved LocalPilot application.")
    return _ALIASES[name]

def _chrome_command() -> list[str] | None:
    candidates = [Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe", Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe"]
    return [str(path)] if next((path for path in candidates if path.is_file()), None) else None

def _vscode_command() -> list[str] | None:
    found = shutil.which("code.exe") or shutil.which("code")
    return [found] if found else None

@needle.tool
def get_current_time() -> str:
    """Get the current local date and time."""
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")

@needle.tool
def open_application(app_name: str) -> str:
    """Open one approved Windows app or settings page. Args: app_name: known app name or alias."""
    app = _canonical(app_name)
    try:
        if app in _URIS:
            os.startfile(_URIS[app])  # URI comes only from the fixed mapping.
        else:
            command = _chrome_command() if app == "chrome" else _vscode_command() if app == "vscode" else _COMMANDS.get(app)
            if not command:
                return f"{app_name} is not installed or could not be located."
            subprocess.Popen(command, shell=False)
    except OSError as exc:
        return f"Could not open {app_name}: {exc}"
    return f"Opened {app_name}."

def _tasklist_rows() -> list[dict[str, str]]:
    completed = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, check=False, shell=False)
    if getattr(completed, "returncode", 0):
        detail = (getattr(completed, "stderr", "") or "tasklist was denied").strip()
        raise RuntimeError(detail)
    output = completed.stdout
    return [{"name": row[0], "pid": row[1]} for row in csv.reader(io.StringIO(output)) if len(row) >= 2 and row[0].lower() not in _BACKGROUND]

@needle.tool
def get_running_applications() -> list[dict[str, str]]:
    """List currently running user-facing applications with name and PID."""
    try:
        return _tasklist_rows()[:40]
    except Exception as exc:
        return [{"error": f"Could not inspect running applications: {exc}"}]

@needle.tool
def is_application_running(app_name: str) -> bool:
    """Check whether a known approved application is currently running."""
    app = _canonical(app_name)
    return any(row["name"].lower() in _PROCESS_NAMES.get(app, set()) for row in _tasklist_rows())

class TimerManager:
    def __init__(self) -> None:
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()
        self.on_update = None
        self.on_finished = None

    def set(self, duration_seconds: int, label: str = "Timer") -> str:
        if not isinstance(duration_seconds, int) or isinstance(duration_seconds, bool) or not 1 <= duration_seconds <= MAX_TIMER_SECONDS:
            raise ValueError("Timer duration must be an integer from 1 second to 24 hours.")
        label = (label or "Timer").strip()[:80]
        with self._lock:
            if self._timer:
                raise ValueError("A LocalPilot timer is already active. Cancel it before starting another.")
            self._timer = threading.Timer(duration_seconds, self._finish, args=(label,))
            self._timer.daemon = True; self._timer.start()
        if self.on_update: self.on_update(label, duration_seconds)
        return f"{label} set for {duration_seconds} seconds. LocalPilot must remain open for the alert."

    def _finish(self, label: str) -> None:
        with self._lock: self._timer = None
        if self.on_finished: self.on_finished(label)

    def cancel(self) -> str:
        with self._lock:
            if not self._timer: return "No LocalPilot timer is active."
            self._timer.cancel(); self._timer = None
        return "Timer cancelled."

timers = TimerManager()

@needle.tool
def set_timer(duration_seconds: Annotated[int, needle.Field(ge=1, le=MAX_TIMER_SECONDS)], label: str = "Timer") -> str:
    """Set one LocalPilot timer. duration_seconds must be 1 to 86400 seconds."""
    return timers.set(duration_seconds, label)

@needle.tool
def cancel_timer() -> str:
    """Cancel the active LocalPilot timer."""
    return timers.cancel()

TOOLS = [get_current_time, open_application, get_running_applications, is_application_running, set_timer, cancel_timer]
