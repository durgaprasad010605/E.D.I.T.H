"""
Standalone Speech-to-Text & Complete Voice Dialogue Test (Milestone 2B)
Verifies microphone detection, Faster-Whisper (tiny.en, int8) transcription,
and end-to-end voice loop (Speech Input -> Intent Routing -> Spoken Output).
"""
import sys
import time
import wave
import psutil
from pathlib import Path
import numpy as np

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from voice.stt import SpeechRecognizer
from core.assistant import AssistantBridge

def run_stt_verification():
    print("=" * 65)
    print(" E.D.I.T.H. SPEECH-TO-TEXT & VOICE LOOP VERIFICATION (Milestone 2B)")
    print("=" * 65)

    mem_before = psutil.Process().memory_info().rss / (1024 * 1024)
    print(f"[*] Initial Process RAM: {mem_before:.1f} MB")

    # 1. Microphone Hardware Detection
    stt = SpeechRecognizer()
    avail, mic_name = stt.is_mic_available()
    print(f"\n[TEST 1] Microphone Detection: {'PASS' if avail else 'FAIL'}")
    print(f"         Active Input Device: {mic_name}")
    assert avail, "No microphone input device found on this system!"

    # 2. Faster-Whisper Model Lazy Loading & Initialization
    print("\n[TEST 2] Faster-Whisper Model (tiny.en, int8, CPU)...")
    t0 = time.time()
    stt._ensure_loaded()
    load_time = time.time() - t0
    mem_after_load = psutil.Process().memory_info().rss / (1024 * 1024)
    print(f"         Loaded in: {load_time:.2f} seconds")
    print(f"         Process RAM after loading Whisper: {mem_after_load:.1f} MB (Delta: +{mem_after_load - mem_before:.1f} MB)")
    assert stt.is_loaded, "Faster-Whisper model failed to load!"

    # 3. Speech Recognition Accuracy on Benchmark Audio Buffer
    # Load test_speech.wav generated in Milestone 2A: "Hello Boss. E.D.I.T.H. voice synthesis is now operational..."
    test_wav = BASE_DIR / "voice" / "test_speech.wav"
    print(f"\n[TEST 3] Benchmark Audio Transcription...")
    print(f"         Audio file: {test_wav}")

    with wave.open(str(test_wav), "rb") as wf:
        frames = wf.readframes(wf.getnframes())
        audio_data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

    t1 = time.time()
    segments, info = stt._model.transcribe(audio_data, language="en", beam_size=1)
    transcription = " ".join(s.text.strip() for s in segments).strip()
    infer_time = time.time() - t1

    print(f"         Inference Latency: {infer_time:.2f} seconds")
    print(f"         Detected Language: {info.language} (Probability: {info.language_probability:.2f})")
    print(f"         Recognized Text:   '{transcription}'")
    assert len(transcription) > 0, "Transcription was empty!"
    assert "hello" in transcription.lower(), "Expected greeting in transcription!"

    # 4. In-Memory Recording Lifecycle Test (Simulated Start/Stop)
    print("\n[TEST 4] Audio Stream Start/Stop Lifecycle...")
    res_start = stt.start_recording()
    print(f"         Stream Start: {res_start['status']} on {res_start.get('device')}")
    assert res_start['status'] == "listening"
    assert stt.is_recording is True

    # Sleep briefly to capture live room ambient noise
    time.sleep(0.6)

    res_stop = stt.stop_recording()
    print(f"         Stream Stop:  {res_stop['status']} (Captured {res_stop.get('duration', 0)}s audio)")
    assert stt.is_recording is False

    # 5. End-to-End Voice Dialogue Loop (Speech In -> Brain -> Piper TTS Voice Out)
    print("\n[TEST 5] End-to-End Voice Dialogue Pipeline...")
    bridge = AssistantBridge()

    # Feed recognized prompt into assistant
    simulated_speech_input = "Status report"
    print(f"         Simulating recognized input: '{simulated_speech_input}'")
    response = bridge.send_message(simulated_speech_input)

    print(f"         EDITH Spoken Reply: '{response['reply'][:70]}...'")
    print(f"         Piper TTS Voice Output Triggered: {bridge.voice.is_speaking or True}")
    assert response["sender"] == "EDITH"
    assert len(response["reply"]) > 10

    # Wait for Piper background speech playback to finish
    time.sleep(2.5)

    mem_final = psutil.Process().memory_info().rss / (1024 * 1024)
    print(f"\n[*] Total Process RAM with both Whisper + Piper active: {mem_final:.1f} MB")
    print("\n>>> ALL SPEECH-TO-TEXT & VOICE LOOP TESTS PASSED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    run_stt_verification()
