"""LocalPilot main window — redesigned dark desktop-assistant interface.

Preserves: microphone capture, Whistle transcription, Needle tool dispatch,
application open/close, timers, running-process queries, and open_website.
"""
from __future__ import annotations

import os
import tempfile
import time

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
import sounddevice as sd

from assistant.microphone import MAX_SECONDS, MicrophoneError, MicrophoneRecorder, write_wav
from assistant.transcription import TranscriptionError, transcribe_wav
from assistant.actions import timers
from assistant.commands import CommandWorker
from ui import theme
from ui.widgets import ActivityBar, MessageBubble, MicButton, StatusDot


# ─── Workers (unchanged logic, extracted from old main_window.py) ────────────

class TimerNotifier(QObject):
    updated = Signal(str, int)
    finished = Signal(str)


class TranscriptionWorker(QObject):
    completed = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, samples) -> None:
        super().__init__()
        self.samples = samples

    def run(self) -> None:
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp:
                temp_path = temp.name
            write_wav(temp_path, self.samples)
            self.completed.emit(transcribe_wav(temp_path))
        except (MicrophoneError, TranscriptionError) as exc:
            self.failed.emit(str(exc))
        except Exception as exc:
            self.failed.emit(f"Unexpected transcription error: {exc}")
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
            self.finished.emit()


# ─── Main window ─────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LocalPilot")
        self.resize(680, 580)
        self.setMinimumSize(420, 400)

        # ── Apply theme ──────────────────────────────────────────────
        self.setStyleSheet(theme.build_stylesheet())

        # ── Core state (preserved from original) ────────────────────
        self.recorder = MicrophoneRecorder()
        self._thread: QThread | None = None
        self._worker: TranscriptionWorker | None = None
        self._command_thread: QThread | None = None
        self._command_worker: CommandWorker | None = None

        # Timer wiring (unchanged logic)
        self._timer_notifier = TimerNotifier(self)
        self._timer_notifier.updated.connect(self._timer_started)
        self._timer_notifier.finished.connect(self._timer_finished)
        timers.on_update = lambda label, seconds: self._timer_notifier.updated.emit(label, seconds)
        timers.on_finished = lambda label: self._timer_notifier.finished.emit(label)
        self._timer_clock = QTimer(self)
        self._timer_clock.timeout.connect(self._timer_tick)
        self._timer_ends_at = 0.0

        # Recording elapsed timer
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.timeout.connect(self._update_elapsed)
        self._started_at = 0.0

        # ── Build UI ────────────────────────────────────────────────
        self._build_ui()

    # ═══════════════════════════════════════════════════════════════════
    # UI construction
    # ═══════════════════════════════════════════════════════════════════

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(20, 16, 20, 14)
        outer.setSpacing(0)

        # A. Header
        outer.addLayout(self._build_header())
        outer.addSpacing(14)

        # B. Conversation area
        outer.addWidget(self._build_conversation(), 1)
        outer.addSpacing(10)

        # D. Activity bar
        self.activity = ActivityBar()
        outer.addWidget(self.activity)
        outer.addSpacing(10)

        # C. Microphone controls
        outer.addLayout(self._build_mic_controls())
        outer.addSpacing(10)

        # E. Footer
        outer.addLayout(self._build_footer())

    # ── A. Header ────────────────────────────────────────────────────
    def _build_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)

        # App icon + title
        icon = QLabel("🧭")
        icon.setStyleSheet(f"font-size: 26px; background: transparent;")
        row.addWidget(icon)

        title = QLabel("LocalPilot")
        title.setObjectName("appTitle")
        row.addWidget(title)

        # Status dot + label
        self.status_dot = StatusDot()
        row.addSpacing(8)
        row.addWidget(self.status_dot)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        row.addWidget(self.status_label)

        row.addStretch()

        # Device selector
        self.device = QComboBox()
        self.device.setMinimumWidth(180)
        self.device.setMaximumWidth(300)
        self._populate_devices()
        row.addWidget(self.device)

        return row

    # ── B. Conversation area ─────────────────────────────────────────
    def _build_conversation(self) -> QFrame:
        card = QFrame()
        card.setObjectName("conversationCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(2, 2, 2, 2)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self._messages_widget = QWidget()
        self._messages_layout = QVBoxLayout(self._messages_widget)
        self._messages_layout.setContentsMargins(12, 12, 12, 12)
        self._messages_layout.setSpacing(10)
        self._messages_layout.addStretch()

        # Welcome placeholder
        welcome = QLabel(
            "Press the microphone button and speak a command.\n"
            "Try: \"Open Chrome\", \"Set a timer for 2 minutes\", or \"Open leetcode.com website.\""
        )
        welcome.setWordWrap(True)
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-size: {theme.FONT_SIZE_MD}; "
            f"padding: 40px 20px; background: transparent;"
        )
        welcome.setObjectName("welcomeLabel")
        self._messages_layout.insertWidget(0, welcome)

        self._scroll.setWidget(self._messages_widget)
        card_layout.addWidget(self._scroll)

        # Timer status row (inside the card, at the bottom)
        self.timer_label = QLabel("")
        self.timer_label.setObjectName("timerLabel")
        self.timer_label.setVisible(False)
        card_layout.addWidget(self.timer_label)

        return card

    # ── C. Microphone controls ───────────────────────────────────────
    def _build_mic_controls(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)

        # Elapsed timer
        self.elapsed_label = QLabel("00:00 / 00:30")
        self.elapsed_label.setObjectName("elapsedLabel")
        self.elapsed_label.setVisible(False)
        row.addWidget(self.elapsed_label)

        row.addStretch()

        self.mic_button = MicButton()
        self.mic_button.clicked.connect(self.toggle_recording)
        row.addWidget(self.mic_button)

        row.addStretch()

        # Clear conversation
        clear_btn = QPushButton("Clear")
        clear_btn.setToolTip("Clear conversation history")
        clear_btn.clicked.connect(self._clear_conversation)
        row.addWidget(clear_btn)

        return row

    # ── E. Footer ────────────────────────────────────────────────────
    def _build_footer(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(6)

        model_label = QLabel("Speech: Whistle")
        model_label.setObjectName("footerLabel")
        row.addWidget(model_label)

        sep = QLabel("·")
        sep.setObjectName("footerLabel")
        row.addWidget(sep)

        self.mic_status_footer = QLabel("Mic: idle")
        self.mic_status_footer.setObjectName("footerLabel")
        row.addWidget(self.mic_status_footer)

        row.addStretch()

        hint = QLabel('Try: "Open Chrome", "Set a timer", or "Open github.com website"')
        hint.setObjectName("hintLabel")
        row.addWidget(hint)

        return row

    # ═══════════════════════════════════════════════════════════════════
    # Conversation management
    # ═══════════════════════════════════════════════════════════════════

    def _add_message(self, text: str, role: str = "assistant") -> None:
        """Append a message bubble to the conversation."""
        # Remove welcome placeholder if present
        welcome = self._messages_widget.findChild(QLabel, "welcomeLabel")
        if welcome:
            welcome.setParent(None)
            welcome.deleteLater()

        bubble = MessageBubble(text, role=role)
        # Insert before the stretch
        count = self._messages_layout.count()
        self._messages_layout.insertWidget(count - 1, bubble)

        # Scroll to bottom on next event loop tick
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self) -> None:
        vbar = self._scroll.verticalScrollBar()
        vbar.setValue(vbar.maximum())

    def _clear_conversation(self) -> None:
        """Remove all message bubbles."""
        while self._messages_layout.count() > 1:
            item = self._messages_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    # ═══════════════════════════════════════════════════════════════════
    # Recording (microphone logic preserved from original)
    # ═══════════════════════════════════════════════════════════════════

    def toggle_recording(self) -> None:
        if self.recorder.recording:
            self.stop_recording()
        elif self._thread is None:
            self.start_recording()

    def start_recording(self) -> None:
        self.recorder.device = self.device.currentData()
        try:
            self.recorder.start()
        except MicrophoneError as exc:
            self._set_error(str(exc))
            return
        self._started_at = time.monotonic()
        self._elapsed_timer.start(100)
        self.elapsed_label.setVisible(True)

        self.mic_button.set_state("listening")
        self.status_dot.set_state("listening")
        self.status_label.setText("Listening…")
        self.mic_status_footer.setText("Mic: recording")
        self.device.setEnabled(False)
        self.activity.set_activity("Recording audio", "🎙️")

    def stop_recording(self) -> None:
        self._elapsed_timer.stop()
        self.elapsed_label.setVisible(False)
        try:
            samples = self.recorder.stop()
        except MicrophoneError as exc:
            self._set_error(str(exc))
            return

        self._set_processing("Transcribing audio with Whistle…")
        self.activity.set_activity("Transcribing audio", "📝")

        self._thread = QThread(self)
        self._worker = TranscriptionWorker(samples)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.completed.connect(self._handle_transcription)
        self._worker.failed.connect(self._set_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._finished)
        self._thread.start()

    def _update_elapsed(self) -> None:
        seconds = min(int(time.monotonic() - self._started_at), MAX_SECONDS)
        self.elapsed_label.setText(f"{seconds // 60:02d}:{seconds % 60:02d} / 00:30")
        if seconds >= MAX_SECONDS:
            self.stop_recording()

    # ═══════════════════════════════════════════════════════════════════
    # Transcription handling (preserved from original)
    # ═══════════════════════════════════════════════════════════════════

    def _handle_transcription(self, result) -> None:
        if result.text:
            self._add_message(result.text, role="user")
            self._run_command(result.text)
        else:
            self._set_ready()
            self.status_label.setText("No speech detected — try again")
            self.activity.set_activity("No speech detected", "🔇")

    # ═══════════════════════════════════════════════════════════════════
    # Command execution (preserved Needle integration)
    # ═══════════════════════════════════════════════════════════════════

    def _run_command(self, text: str) -> None:
        if self._command_thread is not None:
            return
        self._set_processing("Processing command…")
        self.activity.set_activity("Running approved actions", "⚡")

        self._command_thread = QThread(self)
        self._command_worker = CommandWorker(text)
        self._command_worker.moveToThread(self._command_thread)
        self._command_thread.started.connect(self._command_worker.run)
        self._command_worker.completed.connect(self._command_complete)
        self._command_worker.failed.connect(self._command_error)
        self._command_worker.finished.connect(self._command_thread.quit)
        self._command_worker.finished.connect(self._command_worker.deleteLater)
        self._command_thread.finished.connect(self._command_finished)
        self._command_thread.start()

    def _command_complete(self, response) -> None:
        results = response.get("results", []) if isinstance(response, dict) else []
        if results:
            message = "\n".join(str(r) for r in results)
        else:
            message = "No approved action matched your request."
        self._add_message(message, role="assistant")
        self.activity.set_activity("Done", "✅")
        # Auto-reset activity after a delay
        QTimer.singleShot(4000, self.activity.set_idle)

    def _command_error(self, error_msg: str) -> None:
        self._set_error(error_msg)
        self._add_message(f"Error: {error_msg}", role="assistant")

    def _command_finished(self) -> None:
        self._command_worker = None
        if self._command_thread:
            self._command_thread.deleteLater()
            self._command_thread = None
        self._set_ready()

    # ═══════════════════════════════════════════════════════════════════
    # Timer display (preserved from original)
    # ═══════════════════════════════════════════════════════════════════

    def _timer_started(self, label: str, seconds: int) -> None:
        self._timer_ends_at = time.monotonic() + seconds
        self._timer_clock.start(250)
        self.timer_label.setVisible(True)
        self.timer_label.setText(f"⏱ {label} — {seconds}s remaining")

    def _timer_tick(self) -> None:
        remaining = max(0, int(self._timer_ends_at - time.monotonic()))
        self.timer_label.setText(f"⏱ Timer — {remaining}s remaining")

    def _timer_finished(self, label: str) -> None:
        self._timer_clock.stop()
        self.timer_label.setText(f"✅ Timer finished: {label}")
        QTimer.singleShot(8000, lambda: self.timer_label.setVisible(False))
        try:
            import winsound
            winsound.MessageBeep()
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════════════
    # State helpers
    # ═══════════════════════════════════════════════════════════════════

    def _set_ready(self) -> None:
        self.mic_button.set_state("idle")
        self.status_dot.set_state("ready")
        self.status_label.setText("Ready")
        self.mic_status_footer.setText("Mic: idle")

    def _set_processing(self, label: str) -> None:
        self.mic_button.set_state("processing")
        self.status_dot.set_state("processing")
        self.status_label.setText(label)
        self.mic_status_footer.setText("Mic: processing")

    def _set_error(self, message: str) -> None:
        self.mic_button.set_state("error")
        self.status_dot.set_state("error")
        self.status_label.setText(f"Error — {message}")
        self.mic_status_footer.setText("Mic: error")
        self.activity.set_activity(f"Error: {message}", "❌")

    def _finished(self) -> None:
        """Called when the transcription thread completes."""
        self._worker = None
        if self._thread:
            self._thread.deleteLater()
            self._thread = None
        self._set_ready()
        self.device.setEnabled(True)

    # ═══════════════════════════════════════════════════════════════════
    # Device enumeration (preserved from original)
    # ═══════════════════════════════════════════════════════════════════

    def _populate_devices(self) -> None:
        self.device.addItem("System default microphone", None)
        try:
            for index, info in enumerate(sd.query_devices()):
                if info["max_input_channels"]:
                    self.device.addItem(f"{info['name']} ({info['hostapi']})", index)
        except Exception as exc:
            self.device.setEnabled(False)
            self.status_label.setText(f"Could not list microphones: {exc}")

    # ═══════════════════════════════════════════════════════════════════
    # Cleanup (preserved from original)
    # ═══════════════════════════════════════════════════════════════════

    def closeEvent(self, event) -> None:  # noqa: N802
        self._elapsed_timer.stop()
        self._timer_clock.stop()
        self.recorder.close()
        timers.cancel()
        if self._thread:
            self._thread.quit()
            self._thread.wait(3000)
        if self._command_thread:
            self._command_thread.quit()
            self._command_thread.wait(3000)
        event.accept()
