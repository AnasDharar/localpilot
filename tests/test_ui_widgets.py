"""Tests for the redesigned UI widgets and theme module.

These tests instantiate Qt widgets without showing them to verify state logic,
signal wiring, and design-token correctness.  They do not require a GPU or
visible display.
"""
import pytest
from PySide6.QtWidgets import QApplication

from ui import theme
from ui.widgets import ActivityBar, MessageBubble, MicButton, StatusDot


# Reuse the global QApplication that test_transcription_worker already creates,
# or create one if running this file in isolation.
_app = QApplication.instance() or QApplication([])


# ─── StatusDot ───────────────────────────────────────────────────────────────

class TestStatusDot:
    def test_initial_state_is_ready(self):
        dot = StatusDot()
        assert dot._state == "ready"

    def test_set_state_listening(self):
        dot = StatusDot()
        dot.set_state("listening")
        assert dot._state == "listening"

    def test_set_state_ready_stops_pulse(self):
        dot = StatusDot()
        dot.set_state("listening")
        dot.set_state("ready")
        assert dot._state == "ready"
        assert dot._opacity == 1.0

    @pytest.mark.parametrize("state", ["ready", "listening", "processing", "error"])
    def test_all_states_are_accepted(self, state):
        dot = StatusDot()
        dot.set_state(state)
        assert dot._state == state


# ─── MicButton ───────────────────────────────────────────────────────────────

class TestMicButton:
    def test_initial_state_is_idle(self):
        btn = MicButton()
        assert btn._state == "idle"

    def test_set_listening_enables(self):
        btn = MicButton()
        btn.set_state("listening")
        assert btn._state == "listening"
        assert btn._enabled is True

    def test_set_processing_disables(self):
        btn = MicButton()
        btn.set_state("processing")
        assert btn._state == "processing"
        assert btn._enabled is False

    def test_click_signal_emits(self):
        btn = MicButton()
        clicked = []
        btn.clicked.connect(lambda: clicked.append(True))
        btn.clicked.emit()
        assert clicked == [True]

    def test_size_hint(self):
        btn = MicButton()
        s = theme.MIC_SIZE + 16
        assert btn.sizeHint().width() == s
        assert btn.sizeHint().height() == s


# ─── MessageBubble ───────────────────────────────────────────────────────────

class TestMessageBubble:
    def test_user_role(self):
        bubble = MessageBubble("Hello", role="user")
        assert bubble._role == "user"

    def test_assistant_role(self):
        bubble = MessageBubble("Response", role="assistant")
        assert bubble._role == "assistant"


# ─── ActivityBar ─────────────────────────────────────────────────────────────

class TestActivityBar:
    def test_default_is_idle(self):
        bar = ActivityBar()
        assert "Idle" in bar._label.text()

    def test_set_activity(self):
        bar = ActivityBar()
        bar.set_activity("Transcribing audio", "📝")
        assert "Transcribing" in bar._label.text()

    def test_set_idle_resets(self):
        bar = ActivityBar()
        bar.set_activity("Processing", "⚡")
        bar.set_idle()
        assert "Idle" in bar._label.text()


# ─── Theme ───────────────────────────────────────────────────────────────────

class TestTheme:
    def test_stylesheet_is_nonempty(self):
        ss = theme.build_stylesheet()
        assert isinstance(ss, str)
        assert len(ss) > 100

    def test_palette_colors_are_hex(self):
        for attr in ["BG_PRIMARY", "ACCENT", "TEXT_PRIMARY", "SUCCESS", "ERROR"]:
            color = getattr(theme, attr)
            assert color.startswith("#"), f"{attr} = {color}"
