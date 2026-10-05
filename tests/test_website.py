"""Tests for the open_website tool: normalization, validation, browser launch, and edge cases."""
import pytest
from assistant import actions


# ── Normalization ────────────────────────────────────────────────────────────

@pytest.mark.parametrize(("raw", "expected"), [
    ("leetcode.com", "https://leetcode.com"),
    ("www.github.com.", "https://www.github.com"),
    ("https://learn.microsoft.com", "https://learn.microsoft.com"),
    ("GitHub", "https://github.com"),
    ("YouTube", "https://youtube.com"),
    ("leetcode", "https://leetcode.com"),
    ("microsoft learn", "https://learn.microsoft.com"),
    ("  github.com  ", "https://github.com"),
    ("github.com.", "https://github.com"),
    ("http://example.org", "http://example.org"),
    ("https://example.com/path?q=1", "https://example.com/path?q=1"),
    ("example.com:8080/test", "https://example.com:8080/test"),
])
def test_normalize_website_valid(raw, expected):
    assert actions.normalize_website(raw) == expected


# ── Rejection ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw", [
    "",
    "   ",
    "javascript:alert(1)",
    "file:///C:/secret",
    "data:text/html,<h1>hi</h1>",
    "ftp://files.example.com",
    "https://user:pass@example.com",
    "https://user@example.com",
    "https://",
    "https:///no-host",
    "open calculator please",
    # hostname label too long (>63 chars)
    "a" * 64 + ".com",
    # no TLD (single-label hostname)
    "localhost",
])
def test_normalize_website_rejects_invalid(raw):
    with pytest.raises(ValueError):
        actions.normalize_website(raw)


# ── Browser launch via webbrowser.open ───────────────────────────────────────

def test_open_website_calls_webbrowser_open(monkeypatch):
    opened = []
    monkeypatch.setattr(actions.webbrowser, "open", lambda url, new=0: opened.append((url, new)) or True)
    result = actions.open_website("leetcode.com")
    assert opened == [("https://leetcode.com", 2)]
    assert "Opening https://leetcode.com" in result
    assert "not verified" in result.lower() or "not verified" in result


def test_open_website_github(monkeypatch):
    opened = []
    monkeypatch.setattr(actions.webbrowser, "open", lambda url, new=0: opened.append(url) or True)
    result = actions.open_website("GitHub")
    assert opened == ["https://github.com"]
    assert "github.com" in result


def test_open_website_with_full_https_url(monkeypatch):
    opened = []
    monkeypatch.setattr(actions.webbrowser, "open", lambda url, new=0: opened.append(url) or True)
    result = actions.open_website("https://learn.microsoft.com")
    assert opened == ["https://learn.microsoft.com"]
    assert "learn.microsoft.com" in result


def test_open_website_reports_browser_failure(monkeypatch):
    monkeypatch.setattr(actions.webbrowser, "open", lambda url, new=0: False)
    result = actions.open_website("github.com")
    assert "could not open" in result.lower()


def test_open_website_reports_exception(monkeypatch):
    monkeypatch.setattr(actions.webbrowser, "open", lambda url, new=0: (_ for _ in ()).throw(OSError("browser missing")))
    result = actions.open_website("example.com")
    assert "could not" in result.lower()


def test_open_website_rejects_javascript_scheme():
    # The tool itself calls normalize_website which raises ValueError;
    # but the @needle.tool wrapper may or may not catch it.
    # Test the raw function directly.
    with pytest.raises(ValueError):
        actions.normalize_website("javascript:alert(document.cookie)")


def test_open_website_rejects_credentials():
    with pytest.raises(ValueError):
        actions.normalize_website("https://admin:secret@internal.corp.com")


def test_open_website_rejects_empty():
    with pytest.raises(ValueError):
        actions.normalize_website("")


# ── Tool is registered ──────────────────────────────────────────────────────

def test_open_website_in_tools():
    assert actions.open_website in actions.TOOLS


def test_open_application_in_tools():
    assert actions.open_application in actions.TOOLS


# ── Distinction: app vs website ──────────────────────────────────────────────

def test_chrome_is_an_application_not_website(monkeypatch):
    """'Open Google Chrome' should use open_application, not open_website."""
    seen = []
    monkeypatch.setattr(actions, "_chrome_command", lambda: ["C:/Chrome/chrome.exe"])
    monkeypatch.setattr(actions.subprocess, "Popen", lambda cmd, shell=False: seen.append(cmd))
    result = actions.open_application("Google Chrome")
    assert result == "Opened Google Chrome."
    assert seen == [["C:/Chrome/chrome.exe"]]
