"""
E.D.I.T.H. Offline Voice Engine (Milestone 2A)
Powered by Piper TTS (Local ONNX Neural Synthesis)
Runs in background threads to ensure non-blocking UI responsiveness.
"""
import os
import sys
import re
import time
import wave
import queue
import logging
import threading
import winsound
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger("EDITH.Voice")

class VoiceEngine:
    """
    Offline Text-To-Speech engine using Piper TTS with background worker thread,
    graceful audio error recovery, text normalization, and mute controls.
    """

    def __init__(self, model_dir: Optional[Path] = None):
        self.base_dir = Path(__file__).resolve().parent.parent
        self.model_dir = model_dir or (self.base_dir / "voice" / "models")
        self.model_path = self.model_dir / "en_US-amy-medium.onnx"
        self.config_path = self.model_dir / "en_US-amy-medium.onnx.json"
        self.cache_dir = self.base_dir / "data" / "audio_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.wav_path = self.cache_dir / "edith_speech.wav"

        # State flags
        self.is_muted = False
        self.is_speaking = False
        self.is_loaded = False
        self.voice_model = None
        self._load_lock = threading.Lock()

        # Deduplication & queue
        self._last_spoken_text = ""
        self._last_spoken_time = 0.0
        self._speech_queue = queue.Queue()
        self._worker_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self._worker_thread.start()

    def _ensure_loaded(self) -> bool:
        """Lazy-load the Piper ONNX model into memory on demand."""
        if self.is_loaded and self.voice_model is not None:
            return True

        with self._load_lock:
            if self.is_loaded and self.voice_model is not None:
                return True
            try:
                from piper import PiperVoice
                if not self.model_path.exists():
                    logger.error(f"Piper model file missing at: {self.model_path}")
                    return False

                logger.info(f"Loading Piper voice model from: {self.model_path}")
                self.voice_model = PiperVoice.load(
                    str(self.model_path),
                    config_path=str(self.config_path) if self.config_path.exists() else None
                )
                self.is_loaded = True
                logger.info("Piper voice model successfully loaded.")
                return True
            except Exception as e:
                logger.error(f"Failed to initialize Piper voice: {e}")
                self.voice_model = None
                self.is_loaded = False
                return False

    def clean_text_for_speech(self, text: str) -> str:
        """
        Normalize text for clean, natural conversational speech:
        - Removes markdown bullet symbols, asterisks, brackets, hashes
        - Expands common acronyms or clean punctuation
        """
        if not text:
            return ""

        clean = text
        # Remove URLs
        clean = re.sub(r'https?://\S+', '', clean)
        # Remove code blocks ```...```
        clean = re.sub(r'```.*?```', 'code block omitted.', clean, flags=re.DOTALL)
        # Remove inline code `...`
        clean = re.sub(r'`(.*?)`', r'\1', clean)
        # Remove markdown headers and list markers
        clean = re.sub(r'^[#*\-•>]+\s*', '', clean, flags=re.MULTILINE)
        # Remove bold/italic markers
        clean = re.sub(r'[*_~]', '', clean)
        # Expand E.D.I.T.H. acronym cleanly to 'Edith' for natural speech
        clean = re.sub(r'\bE\.D\.I\.T\.H\.\b', 'Edith', clean)
        clean = re.sub(r'\bEDITH\b', 'Edith', clean)
        # Replace multiple dashes or underscores with space
        clean = re.sub(r'[-_]{2,}', ' ', clean)
        # Normalize whitespace
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean

    def speak(self, text: str, priority: bool = False, callback: Optional[Callable] = None):
        """
        Queue text for non-blocking speech synthesis.
        :param text: Raw response string.
        :param priority: If True, purges current queue to speak immediately.
        :param callback: Optional callback invoked when speech concludes.
        """
        if self.is_muted:
            return

        cleaned = self.clean_text_for_speech(text)
        if not cleaned:
            return

        # Deduplication check: ignore if identical message was spoken in last 3 seconds
        now = time.time()
        if cleaned == self._last_spoken_text and (now - self._last_spoken_time) < 3.0:
            logger.info("Skipping duplicate speech directive.")
            return

        if priority:
            self.stop()

        self._speech_queue.put((cleaned, callback))

    def _speech_worker(self):
        """Background daemon processing speech synthesis and audio playback."""
        while True:
            try:
                item = self._speech_queue.get()
                if item is None:
                    break

                text, callback = item
                if self.is_muted:
                    self._speech_queue.task_done()
                    continue

                if not self._ensure_loaded():
                    self._speech_queue.task_done()
                    continue

                self.is_speaking = True
                self._last_spoken_text = text
                self._last_spoken_time = time.time()

                # Synthesize to wav file
                try:
                    with wave.open(str(self.wav_path), "wb") as wav_file:
                        self.voice_model.synthesize_wav(text, wav_file)

                    # Play synchronously inside this worker thread
                    if not self.is_muted and self.wav_path.exists():
                        winsound.PlaySound(str(self.wav_path), winsound.SND_FILENAME)
                except Exception as audio_err:
                    logger.warning(f"Audio playback notice: {audio_err}")
                finally:
                    self.is_speaking = False
                    if callback:
                        try:
                            callback()
                        except Exception:
                            pass
                    self._speech_queue.task_done()

            except Exception as e:
                logger.error(f"Unexpected error in speech worker: {e}")
                self.is_speaking = False

    def stop(self):
        """Immediately interrupt any ongoing speech and clear the queue."""
        try:
            # Drain queue
            while not self._speech_queue.empty():
                try:
                    self._speech_queue.get_nowait()
                    self._speech_queue.task_done()
                except queue.Empty:
                    break

            # Stop Windows sound playback
            winsound.PlaySound(None, winsound.SND_PURGE)
            self.is_speaking = False
        except Exception as e:
            logger.warning(f"Error while stopping speech: {e}")

    def toggle_mute(self) -> bool:
        """Toggle mute state and return new state (True = muted, False = unmuted)."""
        self.is_muted = not self.is_muted
        if self.is_muted:
            self.stop()
        return self.is_muted

    def set_muted(self, muted: bool):
        """Set mute state explicitly."""
        self.is_muted = muted
        if self.is_muted:
            self.stop()

    def test_voice(self, phrase: Optional[str] = None):
        """Test synthesis and audio playback with a confirmation phrase."""
        test_text = phrase or "E.D.I.T.H. voice synthesis test. Subsystems are fully operational, Boss."
        was_muted = self.is_muted
        self.is_muted = False
        self.speak(test_text, priority=True)
        # Restore mute state if it was originally muted after test
        if was_muted:
            threading.Timer(4.0, lambda: self.set_muted(True)).start()

    def status(self) -> dict:
        return {
            "engine": "Piper TTS (Offline)",
            "model": "en_US-amy-medium",
            "is_loaded": self.is_loaded,
            "is_speaking": self.is_speaking,
            "is_muted": self.is_muted
        }
