"""Constrained Windows actions exposed to Needle; no arbitrary command execution."""
from __future__ import annotations

import csv
import ctypes
import io
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
import webbrowser
from datetime import datetime
from typing import Annotated
from urllib.parse import urlsplit, urlunsplit

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
_PROCESS_NAMES = {"calculator": {"calculator.exe", "calc.exe", "calculatorapp.exe"}, "notepad": {"notepad.exe"}, "chrome": {"chrome.exe"}, "explorer": {"explorer.exe"}, "terminal": {"windowsterminal.exe", "wt.exe"}, "paint": {"mspaint.exe"}, "snipping": {"snippingtool.exe"}, "vscode": {"code.exe"}, "taskmanager": {"taskmgr.exe"}, "settings": {"systemsettings.exe"}, "clock": {"time.exe", "clock.exe"}, "sound": {"systemsettings.exe"}, "network": {"systemsettings.exe"}, "bluetooth": {"systemsettings.exe"}, "display": {"systemsettings.exe"}}
_BACKGROUND = {"system", "registry", "smss.exe", "csrss.exe", "wininit.exe", "services.exe", "lsass.exe", "svchost.exe", "dwm.exe", "fontdrvhost.exe", "conhost.exe"}
_WEBSITE_ALIASES = {"github": "github.com", "youtube": "youtube.com", "leetcode": "leetcode.com", "microsoft learn": "learn.microsoft.com"}

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


def normalize_website(website: str) -> str:
    """Normalize a public HTTP(S) URL without interpreting arbitrary prose."""
    candidate = website.strip().rstrip(".,!?:;)\"]}")
    candidate = _WEBSITE_ALIASES.get(candidate.lower(), candidate)
    if not candidate:
        raise ValueError("Please provide a website domain or HTTPS URL.")
    if "://" not in candidate:
        candidate = "https://" + candidate
    try:
        parts = urlsplit(candidate)
        port = parts.port  # Validate malformed port syntax.
    except ValueError as exc:
        raise ValueError("The website address is malformed.") from exc
    if parts.scheme not in {"http", "https"}:
        raise ValueError("Only http and https websites can be opened.")
    if parts.username or parts.password or not parts.hostname:
        raise ValueError("The website address must not contain credentials and needs a hostname.")
    host = parts.hostname
    if len(host) > 253 or "." not in host or any(not label or len(label) > 63 or not label.replace("-", "").isalnum() for label in host.split(".")):
        raise ValueError("Please provide a valid public website hostname.")
    netloc = host if port is None else f"{host}:{port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, ""))

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


@needle.tool(triggers=[r"\b(website|web site|\.com|\.org|\.net|github|youtube|leetcode)\b"])
def open_website(website: str) -> str:
    """Open an http or https public website in the user's default browser. Args: website: domain or URL."""
    url = normalize_website(website)
    try:
        launched = webbrowser.open(url, new=2)
    except Exception as exc:
        return f"Could not request website launch: {exc}"
    if not launched:
        return "Could not open the website. Check the browser configuration."
    return f"Opening {url} in your default browser. The page load was not verified."

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


def _visible_windows(process_names: set[str]) -> list[tuple[int, int]]:
    """Return top-level visible windows whose owning executable is allowlisted."""
    if os.name != "nt":
        raise OSError("Application closing is available only on Windows.")
    user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
    windows: list[tuple[int, int]] = []
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    @callback_type
    def callback(hwnd, _lparam):
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if user32.IsWindowVisible(hwnd):
            process = kernel32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
            if process:
                try:
                    size = ctypes.c_ulong(32768)
                    name = ctypes.create_unicode_buffer(size.value)
                    if kernel32.QueryFullProcessImageNameW(process, 0, name, ctypes.byref(size)):
                        if Path(name.value).name.lower() in process_names:
                            windows.append((int(hwnd), pid.value))
                finally:
                    kernel32.CloseHandle(process)
        return True

    user32.EnumWindows(callback, 0)
    return windows


def _wait_for_windows_closed(process_names: set[str], pids: set[int], timeout_seconds: float = 5.0) -> list[tuple[int, int]]:
    deadline = time.monotonic() + timeout_seconds
    remaining = _visible_windows(process_names)
    while remaining and time.monotonic() < deadline:
        time.sleep(0.1)
        remaining = [window for window in _visible_windows(process_names) if window[1] in pids]
    return remaining


@needle.tool
def close_application(app_name: str) -> str:
    """Request normal close for visible windows of one approved application; never force-kills."""
    app = _canonical(app_name)
    process_names = _PROCESS_NAMES.get(app, set())
    if not process_names:
        return f"{app_name} does not have a safe close target."
    try:
        targets = _visible_windows(process_names)
    except OSError as exc:
        return f"Could not close {app_name}: {exc}"
    if not targets:
        return f"{app_name} is not running with a visible window."
    if os.name != "nt":
        return f"Could not close {app_name}: Application closing is available only on Windows."
    for hwnd, _pid in targets:
        ctypes.windll.user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
    remaining = _wait_for_windows_closed(process_names, {pid for _hwnd, pid in targets})
    if not remaining:
        return f"Closed {app_name} ({len(targets)} window(s))."
    return (f"Requested close for {app_name}, but {len(remaining)} window(s) remain open. "
            "It may have an unsaved-changes dialog or may not have responded.")

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

TOOLS = [get_current_time, open_application, open_website, close_application, get_running_applications, is_application_running, set_timer, cancel_timer]
