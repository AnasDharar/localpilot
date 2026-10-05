import wave
import numpy as np
from assistant.microphone import MicrophoneRecorder, write_wav

def test_wav_serialization(tmp_path):
    path = tmp_path / "audio.wav"; write_wav(path, np.array([-1., 0., 1.], dtype=np.float32))
    with wave.open(str(path)) as f:
        assert (f.getframerate(), f.getnchannels(), f.getnframes()) == (16000, 1, 3)

def test_start_stop_state_without_hardware(monkeypatch):
    class Stream:
        def start(self): pass
        def stop(self): pass
        def close(self): pass
    monkeypatch.setattr("assistant.microphone.sd.check_input_settings", lambda **k: None)
    monkeypatch.setattr("assistant.microphone.sd.InputStream", lambda **k: Stream())
    recorder = MicrophoneRecorder(); recorder.start(); assert recorder.recording
    assert recorder.stop().size == 0; assert not recorder.recording
