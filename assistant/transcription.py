"""Small, defensive wrapper around the documented Whistle API."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import wave

import needle


class TranscriptionError(RuntimeError):
    """An audio file could not be transcribed."""


@dataclass(frozen=True)
class Transcription:
    text: str
    language: str | None = None
    ttft_ms: float | None = None
    decode_tps: float | None = None


def validate_wav(path: str | Path) -> Path:
    path = Path(path)
    if not path.is_file():
        raise TranscriptionError(f"Audio file was not found: {path}")
    try:
        with wave.open(str(path), "rb") as audio:
            if audio.getnframes() == 0:
                raise TranscriptionError("The audio file contains no samples.")
    except TranscriptionError:
        raise
    except (wave.Error, OSError) as exc:
        raise TranscriptionError("The selected file is not a readable WAV file.") from exc
    return path


def transcribe_wav(path: str | Path, *, word_timestamps: bool = False) -> Transcription:
    """Transcribe a WAV file with Whistle without assuming optional result keys."""
    wav_path = validate_wav(path)
    try:
        result = needle.transcribe(str(wav_path), word_timestamps=word_timestamps)
    except Exception as exc:  # Needle raises engine/download/format-specific errors.
        raise TranscriptionError(f"Whistle could not transcribe this audio: {exc}") from exc
    if not isinstance(result, dict):
        raise TranscriptionError("Whistle returned an unexpected result.")
    text = result.get("text", "")
    if not isinstance(text, str):
        raise TranscriptionError("Whistle returned transcript text in an unexpected format.")
    return Transcription(
        text=text.strip(), language=result.get("language"),
        ttft_ms=result.get("ttft_ms"), decode_tps=result.get("decode_tps"),
    )
