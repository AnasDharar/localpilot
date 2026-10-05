"""In-memory, 16 kHz mono microphone capture using sounddevice."""
from __future__ import annotations

import threading
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd
import soxr

SAMPLE_RATE = 16_000
CHANNELS = 1
MAX_SECONDS = 30


class MicrophoneError(RuntimeError):
    pass


class MicrophoneRecorder:
    def __init__(self, sample_rate: int = SAMPLE_RATE, channels: int = CHANNELS, device=None) -> None:
        self.sample_rate, self.channels = sample_rate, channels
        self.device = device
        self._chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._capture_rate = sample_rate
        self._lock = threading.Lock()

    @property
    def recording(self) -> bool:
        return self._stream is not None

    def start(self) -> None:
        if self.recording:
            raise MicrophoneError("Recording is already in progress.")
        self._chunks = []
        try:
            self._capture_rate = self.sample_rate
            try:
                sd.check_input_settings(device=self.device, samplerate=self._capture_rate, channels=self.channels, dtype="float32")
            except Exception:
                info = sd.query_devices(self.device, "input")
                self._capture_rate = int(info["default_samplerate"])
                sd.check_input_settings(device=self.device, samplerate=self._capture_rate, channels=self.channels, dtype="float32")
            self._stream = sd.InputStream(
                device=self.device, samplerate=self._capture_rate, channels=self.channels, dtype="float32", callback=self._callback,
            )
            self._stream.start()
        except Exception as exc:
            self._stream = None
            raise MicrophoneError(f"Could not open the selected microphone: {exc}") from exc

    def _callback(self, indata: np.ndarray, frames: int, time, status) -> None:
        if status:
            # Keep capture alive; UI will still receive the recording and can report no-audio.
            pass
        with self._lock:
            self._chunks.append(indata.copy())

    def stop(self) -> np.ndarray:
        stream, self._stream = self._stream, None
        if stream is None:
            raise MicrophoneError("No recording is in progress.")
        try:
            stream.stop()
            stream.close()
        except Exception as exc:
            raise MicrophoneError(f"Could not stop the microphone cleanly: {exc}") from exc
        with self._lock:
            samples = np.concatenate(self._chunks, axis=0) if self._chunks else np.empty((0, self.channels), dtype=np.float32)
        mono = samples[:, 0]
        if self._capture_rate != self.sample_rate and mono.size:
            mono = soxr.resample(mono, self._capture_rate, self.sample_rate)
        max_samples = self.sample_rate * MAX_SECONDS
        return mono[:max_samples]

    def close(self) -> None:
        if self.recording:
            try:
                self.stop()
            except MicrophoneError:
                pass


def write_wav(path: str | Path, samples: np.ndarray, sample_rate: int = SAMPLE_RATE) -> None:
    """Write normalized float samples to a standards-compatible PCM WAV."""
    data = np.asarray(samples, dtype=np.float32).reshape(-1)
    if data.size == 0:
        raise MicrophoneError("No audio was captured. Check your microphone and try again.")
    pcm = (np.clip(data, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        audio.writeframes(pcm.tobytes())
