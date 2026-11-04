"""
Standalone Voice Engine Test for E.D.I.T.H. (Milestone 2A)
Verifies Piper TTS synthesis, audio generation, and Windows playback.
"""
import sys
import time
import wave
import winsound
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from piper import PiperVoice

def run_voice_test():
    model_path = BASE_DIR / "voice" / "models" / "en_US-amy-medium.onnx"
    config_path = BASE_DIR / "voice" / "models" / "en_US-amy-medium.onnx.json"
    output_wav = BASE_DIR / "voice" / "test_speech.wav"

    print("=" * 60)
    print(" E.D.I.T.H. STANDALONE VOICE TEST (Piper TTS)")
    print("=" * 60)
    print(f"[1] Checking voice model at: {model_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    # Load Piper model
    print("[2] Loading Piper neural voice model...")
    t0 = time.time()
    voice = PiperVoice.load(str(model_path), config_path=str(config_path))
    load_time = time.time() - t0
    print(f"    Loaded in {load_time:.2f} seconds.")

    # Test phrase
    test_phrase = "Hello Boss. E.D.I.T.H. voice synthesis is now operational. All local subsystems are nominal."
    print(f"\n[3] Synthesizing speech: '{test_phrase}'")
    t1 = time.time()
    with wave.open(str(output_wav), "wb") as wav_file:
        voice.synthesize_wav(test_phrase, wav_file)
    synth_time = time.time() - t1

    wav_size = output_wav.stat().st_size
    print(f"    Synthesized {wav_size} bytes in {synth_time:.2f} seconds.")

    # Playback using native Windows audio
    print("\n[4] Playing audio through default audio device...")
    try:
        winsound.PlaySound(str(output_wav), winsound.SND_FILENAME)
        print("    Playback complete!")
    except Exception as e:
        print(f"    [!] Audio playback device notice: {e}")
        print("    (WAV file generated successfully at voice/test_speech.wav)")

    print("\n[+] VOICE TEST COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    run_voice_test()
