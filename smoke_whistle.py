r"""Run independently: .venv\Scripts\python smoke_whistle.py path\to\clip.wav"""
import argparse
import time
from assistant.transcription import TranscriptionError, transcribe_wav

parser = argparse.ArgumentParser(description="Whistle WAV transcription smoke test")
parser.add_argument("wav", help="Path to a WAV clip")
args = parser.parse_args()
started = time.perf_counter()
try:
    result = transcribe_wav(args.wav, word_timestamps=True)
except TranscriptionError as exc:
    raise SystemExit(f"Error: {exc}")
print("Transcript:", result.text or "(empty; Whistle detected silence or steady noise)")
print("Language:", result.language)
print("First token (ms):", result.ttft_ms)
print("Decode speed (tokens/s):", result.decode_tps)
print("Elapsed (s):", round(time.perf_counter() - started, 3))
