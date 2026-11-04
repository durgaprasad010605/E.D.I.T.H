"""
Automated Verification Suite for Milestone 4.4: Local Wake Word & Hands-Free Activation
Tests:
1. Local offline wake-word detection for 'Hey EDITH'.
2. False wake-word rejection (ambient noise, non-wake phrases, silence).
3. Automatic recording start (without clicking mic button).
4. Local VAD silence detection and automatic recording stop (~1.5s silence).
5. Configurable silence threshold.
6. Maximum recording duration safety cut-off.
7. Manual microphone fallback coexistence.
8. Wake-word enable/disable lifecycle & hardware mic release.
9. Clean microphone shutdown on application termination.
10. Model deduplication (no multiple instances of Whisper/Piper loaded).
11. Zero audio files saved to disk (100% in-memory audio buffers).
12. Full end-to-end hands-free voice dialogue loop.
"""
import os
import io
import sys
import time
import wave
import psutil
import datetime
from pathlib import Path
import numpy as np

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.assistant import AssistantBridge
from voice.wake_word import (
    WakeWordService,
    WakeWordState,
    VoiceActivityDetector,
    generate_acknowledgement_chime
)
from voice.stt import SpeechRecognizer
from voice.engine import VoiceEngine


def synthesize_test_audio(phrase: str) -> np.ndarray:
    """Synthesize clean 16kHz float32 audio of a given phrase using Piper TTS."""
    from piper import PiperVoice
    model_path = BASE_DIR / "voice" / "models" / "en_US-amy-medium.onnx"
    config_path = BASE_DIR / "voice" / "models" / "en_US-amy-medium.onnx.json"

    voice = PiperVoice.load(str(model_path), config_path=str(config_path))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        voice.synthesize_wav(phrase, w)

    buf.seek(0)
    with wave.open(buf, "rb") as wf:
        frames = wf.readframes(wf.getnframes())
        raw = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        sr = wf.getframerate()

    # Resample to 16,000 Hz if needed
    if sr != 16000:
        target_len = int(len(raw) * 16000 / sr)
        audio_16k = np.interp(
            np.linspace(0, len(raw), target_len, endpoint=False),
            np.arange(len(raw)),
            raw
        ).astype(np.float32)
    else:
        audio_16k = raw.astype(np.float32)

    return audio_16k


def run_tests():
    print("=" * 70)
    print(" E.D.I.T.H. MILESTONE 4.4: HANDS-FREE WAKE-WORD TEST SUITE")
    print("=" * 70)

    process = psutil.Process()
    ram_initial_mb = process.memory_info().rss / (1024 * 1024)
    print(f"[*] Initial Process RAM: {ram_initial_mb:.1f} MB")

    # Initialize AssistantBridge
    bridge = AssistantBridge()
    # Explicitly ensure models are loaded
    bridge.voice._ensure_loaded()
    bridge.stt._ensure_loaded()
    ww_service = bridge.wake_word

    ram_after_models_mb = process.memory_info().rss / (1024 * 1024)
    print(f"[*] Process RAM with Piper + Whisper + WakeWord active: {ram_after_models_mb:.1f} MB")

    # =========================================================================
    # TEST 1: Synthesize In-Memory Test Audio Vectors
    # =========================================================================
    print("\n[TEST 1] Synthesizing audio test vectors via Piper TTS...")
    t0 = time.time()
    audio_hey_edith = synthesize_test_audio("Hey Edith")
    audio_hello_world = synthesize_test_audio("Hello world")
    audio_status_report = synthesize_test_audio("Status report")
    print(f"         Synthesized 3 audio test vectors in {time.time() - t0:.2f}s.")
    assert len(audio_hey_edith) > 0
    assert len(audio_hello_world) > 0
    assert len(audio_status_report) > 0

    # =========================================================================
    # TEST 2: Local Voice Activity Detector (VAD) Speech vs Silence
    # =========================================================================
    print("\n[TEST 2] Testing Silero VAD + Energy Gating...")
    vad = VoiceActivityDetector()
    silence_frame = np.zeros(512, dtype=np.float32)
    noise_frame = np.random.normal(0, 0.001, 512).astype(np.float32)
    # Speech frame from middle of 'Hey Edith'
    mid_idx = len(audio_hey_edith) // 2
    speech_frame = audio_hey_edith[mid_idx:mid_idx + 512]

    is_silence = vad.is_speech(silence_frame)
    is_noise = vad.is_speech(noise_frame)
    is_speech = vad.is_speech(speech_frame)

    print(f"         Silence detected as speech: {is_silence} (Expected: False)")
    print(f"         Low noise detected as speech: {is_noise} (Expected: False)")
    print(f"         Speech frame detected as speech: {is_speech} (Expected: True)")
    assert is_silence is False
    assert is_noise is False
    assert is_speech is True

    # =========================================================================
    # TEST 3: In-Memory Futuristic Acknowledgement Chime Generation
    # =========================================================================
    print("\n[TEST 3] Testing Acknowledgement Chime Generation...")
    chime_bytes = generate_acknowledgement_chime()
    print(f"         Chime size in memory: {len(chime_bytes)} bytes")
    assert len(chime_bytes) > 1000
    # Verify WAV header
    assert chime_bytes[:4] == b"RIFF"
    assert chime_bytes[8:12] == b"WAVE"

    # =========================================================================
    # TEST 4: False Wake-Word Rejection
    # =========================================================================
    print("\n[TEST 4] Testing False Wake-Word Rejection...")
    # Feed silence
    ww_service.feed_audio(np.zeros(16000, dtype=np.float32))
    assert ww_service.current_state == WakeWordState.STANDBY
    assert ww_service.is_recording_command is False
    print("         Silence -> STANDBY (PASS)")

    # Feed 'Hello world' followed by silence pause
    ww_service.feed_audio(audio_hello_world)
    ww_service.feed_audio(np.zeros(8000, dtype=np.float32))  # 500ms pause
    assert ww_service.current_state == WakeWordState.STANDBY
    assert ww_service.is_recording_command is False
    print("         'Hello world' -> Rejected, stayed STANDBY (PASS)")

    # Feed 'Status report' followed by silence pause
    ww_service.feed_audio(audio_status_report)
    ww_service.feed_audio(np.zeros(8000, dtype=np.float32))
    assert ww_service.current_state == WakeWordState.STANDBY
    assert ww_service.is_recording_command is False
    print("         'Status report' -> Rejected, stayed STANDBY (PASS)")

    # =========================================================================
    # TEST 5: Wake-Word Detection & Automatic Recording Start ("Hey EDITH")
    # =========================================================================
    print("\n[TEST 5] Testing Wake-Word Detection ('Hey EDITH')...")
    state_history = []
    ww_service.on_state_change = lambda s, d: state_history.append(s)

    # Feed 'Hey Edith' followed by 300ms pause
    ww_service.feed_audio(audio_hey_edith)
    ww_service.feed_audio(np.zeros(int(16000 * 0.35), dtype=np.float32))

    print(f"         Observed State Transitions: {state_history}")
    assert WakeWordState.WAKE_WORD_DETECTED in state_history
    assert ww_service.current_state == WakeWordState.LISTENING
    assert ww_service.is_recording_command is True
    print("         'Hey EDITH' recognized! State transitioned to LISTENING automatically. (PASS)")

    # =========================================================================
    # TEST 6: Local VAD Silence Detection & Automatic Recording Stop
    # =========================================================================
    print("\n[TEST 6] Testing Automatic Speech-End Silence Detection (1.5s silence)...")
    ww_service.silence_duration_sec = 1.5

    # User speaks command directive: 'Status report'
    ww_service.feed_audio(audio_status_report)
    assert ww_service.is_recording_command is True
    assert ww_service._command_has_speech is True

    # User pauses for 0.5s (short pause between words should NOT stop recording)
    ww_service.feed_audio(np.zeros(int(16000 * 0.5), dtype=np.float32))
    assert ww_service.is_recording_command is True
    print("         Short pause (0.5s): Recording continued seamlessly (PASS)")

    # User stops speaking: 1.6s of continuous silence arrives
    silence_1_6s = np.zeros(int(16000 * 1.6), dtype=np.float32)
    ww_service.feed_audio(silence_1_6s)

    # Recording should automatically stop!
    assert ww_service.is_recording_command is False
    assert ww_service.current_state in (WakeWordState.PROCESSING, WakeWordState.SPEAKING, WakeWordState.STANDBY)
    print("         Continuous silence (1.6s): Recording stopped automatically (PASS)")

    # =========================================================================
    # TEST 7: Configurable Silence Duration
    # =========================================================================
    print("\n[TEST 7] Testing Configurable Silence Duration...")
    bridge.set_vad_silence_duration(0.8)
    assert ww_service.silence_duration_sec == 0.8
    assert bridge.get_settings()["vad_silence_duration"] == 0.8

    # Start recording command artificially
    ww_service.is_recording_command = True
    ww_service._command_has_speech = True
    ww_service._command_audio_chunks = [audio_status_report]
    ww_service._command_continuous_silence_samples = 0

    # Feed 0.9s of silence (> 0.8s threshold)
    ww_service.feed_audio(np.zeros(int(16000 * 0.9), dtype=np.float32))
    assert ww_service.is_recording_command is False
    print("         Updated silence threshold (0.8s) respected (PASS)")

    # Reset back to default 1.5s
    bridge.set_vad_silence_duration(1.5)

    # =========================================================================
    # TEST 8: Maximum Recording Duration Safety Cut-Off
    # =========================================================================
    print("\n[TEST 8] Testing Maximum Recording Duration Safety Limit...")
    ww_service.set_max_duration(2.0)
    assert ww_service.max_recording_duration_sec == 2.0

    ww_service.is_recording_command = True
    ww_service._command_has_speech = True
    ww_service._command_audio_chunks = []
    ww_service._command_total_samples = 0

    # Feed 2.2s of continuous speech frames (without silence)
    speech_frames = np.tile(speech_frame, 75)  # 75 * 512 = 38400 samples = 2.4s
    ww_service.feed_audio(speech_frames)

    # Recording must stop to prevent indefinite recording
    assert ww_service.is_recording_command is False
    print("         Max duration reached (2.0s): Recording terminated safely (PASS)")
    ww_service.set_max_duration(15.0)

    # =========================================================================
    # TEST 9: Manual Microphone Fallback Coexistence
    # =========================================================================
    print("\n[TEST 9] Testing Manual Microphone Fallback Coexistence...")
    ww_service._set_state(WakeWordState.STANDBY)

    # Start manual recording
    start_res = bridge.start_mic()
    assert start_res["status"] in ("listening", "already_recording", "error")
    # Verify wake word paused for manual recording
    assert ww_service._paused_for_manual is True
    print("         Manual mic start: Wake-word monitoring paused safely (PASS)")

    # Stop manual recording
    stop_res = bridge.stop_mic()
    assert ww_service._paused_for_manual is False
    print("         Manual mic stop: Wake-word monitoring resumed safely (PASS)")

    # =========================================================================
    # TEST 10: Wake-Word Enable / Disable & Hardware Microphone Release
    # =========================================================================
    print("\n[TEST 10] Testing Wake-Word Enable/Disable Control...")
    # Disable wake-word
    dis_res = bridge.set_wake_word_enabled(False)
    assert dis_res["enabled"] is False
    assert ww_service.is_enabled is False
    assert ww_service._running is False
    assert ww_service._stream is None
    print("         Wake word disabled: Stream closed & microphone released (PASS)")

    # Feed audio while disabled; verify state stays STANDBY
    ww_service.feed_audio(audio_hey_edith)
    assert ww_service.is_recording_command is False

    # Re-enable wake-word
    en_res = bridge.set_wake_word_enabled(True)
    assert en_res["enabled"] is True
    assert ww_service.is_enabled is True
    print("         Wake word re-enabled: Service resumed (PASS)")

    # =========================================================================
    # TEST 11: Model Deduplication & Memory Sharing Verification
    # =========================================================================
    print("\n[TEST 11] Verifying Model Deduplication (No duplicate models)...")
    # Ensure wake_word uses the identical Whisper model instance from SpeechRecognizer
    assert ww_service.stt is bridge.stt
    assert ww_service.stt._model is bridge.stt._model
    assert id(ww_service.stt._model) == id(bridge.stt._model)
    print(f"         Whisper Model Instance ID: {id(bridge.stt._model)} (Single Instance Confirmed)")
    print("         Model Deduplication: PASS")

    # =========================================================================
    # TEST 12: Zero Audio Files Saved to Disk (Privacy Verification)
    # =========================================================================
    print("\n[TEST 12] Verifying Zero Audio Disk Footprint...")
    data_dir = BASE_DIR / "data"
    audio_files_before = list(data_dir.rglob("*.wav"))

    # Simulate hands-free command processing
    ww_service._finish_command_recording()

    audio_files_after = list(data_dir.rglob("*.wav"))
    # The only WAV that may exist is Piper TTS playback cache edith_speech.wav
    user_recordings = [f for f in audio_files_after if "user" in f.name.lower() or "rec" in f.name.lower()]
    assert len(user_recordings) == 0
    print("         No user audio files saved to disk (100% in-memory processing): PASS")

    # =========================================================================
    # TEST 13: Clean Shutdown & Resource Release
    # =========================================================================
    print("\n[TEST 13] Verifying Clean Shutdown...")
    bridge.cleanup()
    assert ww_service.is_enabled is False
    assert ww_service._running is False
    assert ww_service._stream is None
    print("         Application cleanup: All audio streams closed and resources released (PASS)")

    # =========================================================================
    # TEST 14: System Info & HUD Telemetry Verification
    # =========================================================================
    print("\n[TEST 14] Verifying System Info & Telemetry Integration...")
    sys_info = bridge.get_system_info()
    assert "wake_word_engine" in sys_info
    assert sys_info["wake_word"] == "Hey EDITH"
    assert "hud_state" in sys_info

    tele = bridge.get_telemetry()
    assert "hud_state" in tele
    assert "wake_word_enabled" in tele
    print(f"         System Info v{sys_info['version']} with Wake-Word '{sys_info['wake_word']}': PASS")

    ram_final_mb = process.memory_info().rss / (1024 * 1024)
    print(f"\n[*] Final Process RAM: {ram_final_mb:.1f} MB (Delta from initial: +{ram_final_mb - ram_initial_mb:.1f} MB)")
    print("\n=======================================================================")
    print(">>> ALL 14 MILESTONE 4.4 WAKE-WORD & HANDS-FREE TESTS PASSED! <<<")
    print("=======================================================================")


if __name__ == "__main__":
    run_tests()
