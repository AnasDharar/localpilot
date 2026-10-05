import numpy as np
from PySide6.QtCore import QCoreApplication, QEventLoop, QThread

from assistant.transcription import Transcription
from ui.main_window import TranscriptionWorker


def test_worker_completes_off_gui_thread(monkeypatch):
    # This verifies the worker's completion signal reaches the event loop without
    # needing a microphone, model download, or GUI interaction.
    app = QCoreApplication.instance() or QCoreApplication([])
    monkeypatch.setattr("ui.main_window.transcribe_wav", lambda path: Transcription("done", "en"))
    worker, thread, loop, outcomes = TranscriptionWorker(np.zeros(16, dtype=np.float32)), QThread(), QEventLoop(), []
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.completed.connect(lambda result: outcomes.append(result.text))
    worker.failed.connect(lambda error: outcomes.append(f"error: {error}"))
    worker.finished.connect(thread.quit)
    thread.finished.connect(loop.quit)
    thread.start(); loop.exec()
    worker.deleteLater(); thread.deleteLater()
    assert outcomes == ["done"]
