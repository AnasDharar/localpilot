
import needle
import time

print("Whistle transcription test")
print("Speak clearly into your microphone.")

audio_file = input("Enter the path to a WAV file: ").strip().strip('"')

start = time.perf_counter()

result = needle.transcribe(
    audio_file,
    word_timestamps=True,
)

elapsed = time.perf_counter() - start

print("\n--- TRANSCRIPTION ---")
print(result.get("text", ""))

print("\n--- METRICS ---")
print("Language:", result.get("language"))
print("Elapsed time (s):", round(elapsed, 3))
print("First token (ms):", result.get("ttft_ms"))
print("Decode speed (tokens/s):", result.get("decode_tps"))

print("\n--- WORD TIMESTAMPS ---")
for word in result.get("words", []):
    print(word)
