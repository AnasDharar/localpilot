# LocalPilot (Phase 1 + Phase 4)

LocalPilot is a small Windows desktop prototype for local microphone capture and local Whistle transcription. It deliberately has **no computer-control, shell, file, or application-launching tools**. `smoke_needle.py` only exposes an `echo_text` function.

## Requirements and setup

Windows, Python 3.9+, and a working input microphone are required. In PowerShell:

```powershell
cd E:\localpilot
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

The project uses `cactus-needle[mic]` (the official microphone extra includes NumPy, soxr, and sounddevice), PySide6, and pytest. The first Whistle or Needle inference can download its local engine/model weights from Hugging Face; later transcription is local. No credentials are needed.

## Use

Press **Start recording**, speak, then press **Stop recording**. The clip sent to Whistle is 16 kHz mono and capped at 30 seconds. If a microphone cannot open at 16 kHz, LocalPilot captures at its supported default rate and locally resamples to 16 kHz. The temporary WAV used for inference is deleted immediately afterwards. The status text reports Ready, Recording, Transcribing, Complete, and actionable errors.

Choose **System default microphone** or an input device from the selector. If it cannot open, verify Windows Settings > System > Sound input and Settings > Privacy & security > Microphone access, then try the device's Windows WASAPI entry when available.

## Approved voice actions

After transcription, LocalPilot sends the text to Needle with a fixed tool allowlist. It cannot execute arbitrary shell commands, paths, Python, or unregistered functions. Supported examples:

- "What time is it?"
- "Open Calculator", "Open Notepad", "Open Chrome", "Open File Explorer", "Open Windows Terminal", "Open Paint", "Open Snipping Tool", or "Open VS Code" (when installed).
- "Open Settings", "Open Task Manager", "Open Clock", "Open sound settings", "Open Wi-Fi settings", "Open Bluetooth settings", or "Open display settings".
- "Close Chrome", "Close Calculator", "Close Notepad", "Close File Explorer", "Close Windows Terminal", "Close VS Code", "Close Paint", "Close Settings", "Close Task Manager", or "Close Clock".
- "Which applications are running?" and "Is Chrome running?"
- "Set a timer for 60 seconds" and "Cancel my timer."

Application names are aliases for a predefined allowlist. Settings pages use fixed `ms-settings:` URIs, desktop apps use fixed executable names or detected Chrome/VS Code installations, and launches never use `shell=True`. The current timer supports one timer at a time, displays its remaining time, and plays a Windows alert when complete. It works only while LocalPilot remains open; it will not survive app exit or shutdown.

For reliable model argument grounding, simple spoken timer durations (for example, "one minute" and "five minutes") are converted locally to explicit seconds before the approved `set_timer` tool is selected.

Application closing is limited to the same approved aliases. LocalPilot enumerates only visible top-level windows owned by exact allowlisted executable names, sends a normal Windows `WM_CLOSE` request, and checks whether those windows disappear. It does not force-kill an application. If a window remains, LocalPilot warns that an unsaved-changes dialog or an unresponsive application may be blocking closure; respond to that dialog directly. Force-close is deliberately not implemented because it requires an explicit GUI confirmation flow.

## Independent smoke tests

```powershell
.\.venv\Scripts\python.exe smoke_whistle.py C:\path\to\clip.wav
.\.venv\Scripts\python.exe smoke_needle.py
.\.venv\Scripts\python.exe -m pytest
```

`smoke_whistle.py` handles missing/non-WAV/empty files, prints the transcript and only documented result metadata. `smoke_needle.py` may trigger the first-run Needle model download and prints the safe function-call/result structure.

## Limits and privacy

Whistle accepts 16 kHz mono audio up to 30 seconds per pass and supports English, German, French, Spanish, Italian, Dutch, and Polish. Silence or steady noise legitimately returns an empty transcript. Audio is not persisted and transcripts are not logged. The optional global hotkey was intentionally not added: the visible start/stop control is the reliable interaction in this prototype.

Needle telemetry is enabled by default by the upstream binary. Set `NEEDLE_TELEMETRY=0` and `DO_NOT_TRACK=1` before launch to disable it, for example:

```powershell
$env:NEEDLE_TELEMETRY = "0"
$env:DO_NOT_TRACK = "1"
python app.py
```

## References

- [Cactus Needle and Whistle](https://github.com/cactus-compute/needle)
- [Needle API reference for coding agents](https://github.com/cactus-compute/needle/blob/main/llms.txt)
- [PySide6 documentation](https://doc.qt.io/qtforpython-6/)
- [python-sounddevice documentation](https://python-sounddevice.readthedocs.io/)

## Verification

`pytest` covers mocked Whistle success/empty/error handling, WAV serialization, recording state transitions, a Qt background worker, fixed app-launch mappings, process filtering, timer cancellation, and a real one-second timer completion. Application launches and process-list test data are mocked; no test opens an application. Manual microphone transcription and the two genuine model smoke tests require an accessible microphone/model cache and are intentionally reported separately when run.
