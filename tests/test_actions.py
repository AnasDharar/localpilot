import threading

import pytest

from assistant import actions


@pytest.mark.parametrize("app_name, expected", [("Calculator", ["calc.exe"]), ("Task Manager", ["taskmgr.exe"]), ("Notepad", ["notepad.exe"])])
def test_approved_executables_are_launched_with_argument_list(monkeypatch, app_name, expected):
    seen = []
    monkeypatch.setattr(actions.subprocess, "Popen", lambda command, shell=False: seen.append((command, shell)))
    assert actions.open_application(app_name) == f"Opened {app_name}."
    assert seen == [(expected, False)]

@pytest.mark.parametrize("app_name, uri", [("Settings", "ms-settings:"), ("Clock", "ms-clock:"), ("Wi-Fi settings", "ms-settings:network-wifi")])
def test_settings_use_fixed_uri_mapping(monkeypatch, app_name, uri):
    seen = []
    monkeypatch.setattr(actions.os, "startfile", lambda target: seen.append(target), raising=False)
    assert actions.open_application(app_name) == f"Opened {app_name}."
    assert seen == [uri]

def test_unknown_application_is_rejected():
    with pytest.raises(ValueError, match="not an approved"):
        actions.open_application("powershell -command whoami")


def test_close_one_window_posts_normal_close_and_verifies(monkeypatch):
    calls, states = [], [[(101, 44)], []]
    monkeypatch.setattr(actions.os, "name", "nt", raising=False)
    monkeypatch.setattr(actions, "_visible_windows", lambda names: states.pop(0))
    monkeypatch.setattr(actions, "_wait_for_windows_closed", lambda names, pids: [])
    class User32:
        def PostMessageW(self, hwnd, message, wparam, lparam): calls.append((hwnd, message))
    monkeypatch.setattr(actions.ctypes, "windll", type("Dll", (), {"user32": User32()})(), raising=False)
    assert actions.close_application("Notepad") == "Closed Notepad (1 window(s))."
    assert calls == [(101, 0x0010)]


def test_close_multiple_windows_posts_each_and_reports_unsaved_dialog(monkeypatch):
    calls = []
    monkeypatch.setattr(actions.os, "name", "nt", raising=False)
    monkeypatch.setattr(actions, "_visible_windows", lambda names: [(101, 44), (102, 45)])
    monkeypatch.setattr(actions, "_wait_for_windows_closed", lambda names, pids: [(102, 45)])
    class User32:
        def PostMessageW(self, hwnd, message, wparam, lparam): calls.append(hwnd)
    monkeypatch.setattr(actions.ctypes, "windll", type("Dll", (), {"user32": User32()})(), raising=False)
    result = actions.close_application("Notepad")
    assert calls == [101, 102]
    assert "unsaved-changes dialog" in result


def test_close_application_not_running(monkeypatch):
    monkeypatch.setattr(actions.os, "name", "nt", raising=False)
    monkeypatch.setattr(actions, "_visible_windows", lambda names: [])
    assert actions.close_application("Notepad") == "Notepad is not running with a visible window."


def test_chrome_alias_uses_detected_chrome(monkeypatch):
    seen = []
    monkeypatch.setattr(actions, "_chrome_command", lambda: ["C:/Chrome/chrome.exe"])
    monkeypatch.setattr(actions.subprocess, "Popen", lambda command, shell=False: seen.append((command, shell)))
    assert actions.open_application("Google Chrome") == "Opened Google Chrome."
    assert seen == [(["C:/Chrome/chrome.exe"], False)]


def test_current_time_returns_a_nonempty_local_value():
    assert actions.get_current_time()


@pytest.mark.parametrize(("raw", "expected"), [("leetcode.com", "https://leetcode.com"), ("www.github.com.", "https://www.github.com"), ("https://learn.microsoft.com", "https://learn.microsoft.com"), ("GitHub", "https://github.com")])
def test_website_normalization(raw, expected):
    assert actions.normalize_website(raw) == expected


@pytest.mark.parametrize("raw", ["", "javascript:alert(1)", "file:///C:/secret", "https://user:pass@example.com", "open calculator please", "https://"])
def test_invalid_website_is_rejected(raw):
    with pytest.raises(ValueError):
        actions.normalize_website(raw)


def test_open_website_uses_default_browser(monkeypatch):
    opened = []
    monkeypatch.setattr(actions.webbrowser, "open", lambda url, new=0: opened.append((url, new)) or True)
    result = actions.open_website("leetcode.com")
    assert opened == [("https://leetcode.com", 2)]
    assert "Opening https://leetcode.com" in result


def test_open_website_reports_browser_failure(monkeypatch):
    monkeypatch.setattr(actions.webbrowser, "open", lambda url, new=0: False)
    assert "Could not open the website" in actions.open_website("github.com")

def test_process_listing_filters_background_and_running_check(monkeypatch):
    class Result: stdout = '"chrome.exe","42","Console","1","10 K"\n"svchost.exe","9","Services","0","10 K"\n'
    monkeypatch.setattr(actions.subprocess, "run", lambda *a, **k: Result())
    assert actions.get_running_applications() == [{"name": "chrome.exe", "pid": "42"}]
    assert actions.is_application_running("Chrome") is True

def test_timer_finishes_and_can_be_cancelled():
    manager, done = actions.TimerManager(), threading.Event()
    manager.on_finished = lambda label: done.set()
    assert "set for 1 seconds" in manager.set(1, "Test")
    assert done.wait(2.5)
    assert "set for 10 seconds" in manager.set(10)
    assert manager.cancel() == "Timer cancelled."
    assert manager.cancel() == "No LocalPilot timer is active."

@pytest.mark.parametrize("duration", [0, -1, 86401, True, "60"])
def test_invalid_timer_duration_is_rejected(duration):
    with pytest.raises(ValueError):
        actions.TimerManager().set(duration)
