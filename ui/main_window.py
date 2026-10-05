from __future__ import annotations

import os
import tempfile
import time

from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtWidgets import QApplication, QComboBox, QHBoxLayout, QLabel, QMainWindow, QPushButton, QTextEdit, QVBoxLayout, QWidget
import sounddevice as sd

from assistant.microphone import MAX_SECONDS, MicrophoneError, MicrophoneRecorder, write_wav
from assistant.transcription import TranscriptionError, transcribe_wav
from assistant.actions import timers
from assistant.commands import CommandWorker


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
                try: os.unlink(temp_path)
                except OSError: pass
            self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.recorder = MicrophoneRecorder()
        self._thread: QThread | None = None
        # Keep a Python reference.  Qt's signal connections alone do not retain a
        # moved QObject, and an early collection leaves the window permanently in
        # its transcribing state.
        self._worker: TranscriptionWorker | None = None
        self._command_thread: QThread | None = None
        self._command_worker: CommandWorker | None = None
        self._timer_notifier = TimerNotifier(self)
        self._timer_notifier.updated.connect(self._timer_started)
        self._timer_notifier.finished.connect(self._timer_finished)
        timers.on_update = lambda label, seconds: self._timer_notifier.updated.emit(label, seconds)
        timers.on_finished = lambda label: self._timer_notifier.finished.emit(label)
        self._timer_clock = QTimer(self)
        self._timer_clock.timeout.connect(self._timer_tick)
        self._timer_ends_at = 0.0
        self._elapsed = QTimer(self)
        self._elapsed.timeout.connect(self._update_elapsed)
        self._started_at = 0.0
        self.setWindowTitle("LocalPilot")
        self.resize(620, 410)
        root, layout = QWidget(), QVBoxLayout()
        root.setLayout(layout); self.setCentralWidget(root)
        title = QLabel("LocalPilot"); title.setStyleSheet("font-size: 24px; font-weight: 600;")
        self.status = QLabel("Ready — press Start recording to use the default microphone.")
        self.device = QComboBox(); self._populate_devices()
        self.elapsed = QLabel("00:00 / 00:30")
        self.timer_status = QLabel("No active LocalPilot timer")
        self.record = QPushButton("Start recording")
        self.record.setMinimumHeight(52); self.record.clicked.connect(self.toggle_recording)
        self.transcript = QTextEdit(); self.transcript.setPlaceholderText("Your recognized speech will appear here.")
        self.clear = QPushButton("Clear transcript"); self.clear.clicked.connect(self.transcript.clear)
        controls = QHBoxLayout(); controls.addWidget(self.elapsed); controls.addStretch(); controls.addWidget(self.clear)
        for widget in (title, self.status, self.device, self.record, self.transcript, self.timer_status): layout.addWidget(widget)
        layout.addLayout(controls)

    def toggle_recording(self) -> None:
        if self.recorder.recording: self.stop_recording()
        elif self._thread is None: self.start_recording()

    def start_recording(self) -> None:
        self.recorder.device = self.device.currentData()
        try:
            self.recorder.start()
        except MicrophoneError as exc:
            self.set_error(str(exc)); return
        self._started_at = time.monotonic(); self._elapsed.start(100)
        self.record.setText("Stop recording"); self.device.setEnabled(False); self.status.setText("Recording — press Stop when finished.")

    def stop_recording(self) -> None:
        self._elapsed.stop()
        try: samples = self.recorder.stop()
        except MicrophoneError as exc:
            self.set_error(str(exc)); return
        self.status.setText("Transcribing locally with Whistle…"); self.record.setEnabled(False)
        self._thread = QThread(self)
        self._worker = TranscriptionWorker(samples)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.completed.connect(self._handle_transcription); self._worker.failed.connect(self.set_error)
        self._worker.finished.connect(self._thread.quit); self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._finished); self._thread.start()

    def _update_elapsed(self) -> None:
        seconds = min(int(time.monotonic() - self._started_at), MAX_SECONDS)
        self.elapsed.setText(f"{seconds // 60:02d}:{seconds % 60:02d} / 00:30")
        if seconds >= MAX_SECONDS: self.stop_recording()

    def show_transcript(self, result) -> None:
        self.transcript.setPlainText(result.text)
        if result.text:
            self.status.setText(f"Complete — language: {result.language or 'unknown'}; first token: {result.ttft_ms or 'n/a'} ms.")
        else: self.status.setText("Complete — no speech detected. Check microphone input and try again.")

    def _handle_transcription(self, result) -> None:
        self.show_transcript(result)
        if result.text:
            self._run_command(result.text)

    def _run_command(self, text: str) -> None:
        if self._command_thread is not None:
            return
        self.status.setText("Processing approved LocalPilot actions...")
        self._command_thread = QThread(self)
        self._command_worker = CommandWorker(text)
        self._command_worker.moveToThread(self._command_thread)
        self._command_thread.started.connect(self._command_worker.run)
        self._command_worker.completed.connect(self._command_complete)
        self._command_worker.failed.connect(self.set_error)
        self._command_worker.finished.connect(self._command_thread.quit)
        self._command_worker.finished.connect(self._command_worker.deleteLater)
        self._command_thread.finished.connect(self._command_finished)
        self._command_thread.start()

    def _command_complete(self, response) -> None:
        results = response.get("results", []) if isinstance(response, dict) else []
        message = "; ".join(map(str, results)) if results else "no approved action matched."
        self.status.setText(f"Complete - {message}")

    def _command_finished(self) -> None:
        self._command_worker = None
        if self._command_thread:
            self._command_thread.deleteLater()
            self._command_thread = None

    def _timer_started(self, label: str, seconds: int) -> None:
        self._timer_ends_at = time.monotonic() + seconds
        self._timer_clock.start(250)
        self.timer_status.setText(f"Timer: {label} - {seconds}s remaining")

    def _timer_tick(self) -> None:
        remaining = max(0, int(self._timer_ends_at - time.monotonic()))
        self.timer_status.setText(f"Timer active - {remaining}s remaining")

    def _timer_finished(self, label: str) -> None:
        self._timer_clock.stop()
        self.timer_status.setText(f"Timer finished: {label}")
        try:
            import winsound
            winsound.MessageBeep()
        except Exception:
            pass

    def set_error(self, message: str) -> None:
        self.status.setText(f"Error — {message}")

    def _finished(self) -> None:
        self._worker = None
        if self._thread:
            self._thread.deleteLater(); self._thread = None
        self.record.setEnabled(True); self.record.setText("Start recording")
        self.device.setEnabled(True)

    def _populate_devices(self) -> None:
        self.device.addItem("System default microphone", None)
        try:
            for index, info in enumerate(sd.query_devices()):
                if info["max_input_channels"]:
                    self.device.addItem(f"{info['name']} ({info['hostapi']})", index)
        except Exception as exc:
            self.device.setEnabled(False)
            self.status.setText(f"Error — could not list microphones: {exc}")

    def closeEvent(self, event) -> None:
        self._elapsed.stop(); self._timer_clock.stop(); self.recorder.close(); timers.cancel()
        if self._thread:
            self._thread.quit(); self._thread.wait(3000)
        if self._command_thread:
            self._command_thread.quit(); self._command_thread.wait(3000)
        event.accept()
