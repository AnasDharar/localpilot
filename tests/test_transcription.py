import wave
import pytest
from assistant.transcription import TranscriptionError, transcribe_wav

def wav(path, frames=b"\0\0"):
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(16000); f.writeframes(frames)

def test_valid_mocked_result(tmp_path, monkeypatch):
    path = tmp_path / "clip.wav"; wav(path)
    monkeypatch.setattr("assistant.transcription.needle.transcribe", lambda *a, **k: {"text": "hello", "language": "en", "ttft_ms": 4})
    assert transcribe_wav(path).text == "hello"

def test_empty_transcript_is_safe(tmp_path, monkeypatch):
    path = tmp_path / "clip.wav"; wav(path)
    monkeypatch.setattr("assistant.transcription.needle.transcribe", lambda *a, **k: {"text": ""})
    assert transcribe_wav(path).text == ""

def test_missing_audio_has_useful_error():
    with pytest.raises(TranscriptionError, match="not found"):
        transcribe_wav("missing.wav")
