"""
E.D.I.T.H. Offline Speech-to-Text (STT) Module (Milestone 2B)
Powered by Faster-Whisper (tiny.en, int8, CPU) and sounddevice.
100% Local, Offline, In-Memory audio processing with zero disk footprint.
"""
import time
import logging
import threading
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import numpy as np
import sounddevice as sd

logger = logging.getLogger("EDITH.STT")

class SpeechRecognizer:
    """
    Offline speech recognition engine using Faster-Whisper.
    Captures microphone audio in memory, transcribes using INT8 CPU quantization,
    and guarantees zero permanent storage of user voice recordings.
    """

    def __init__(self, model_root: Optional[Path] = None):
        self.base_dir = Path(__file__).resolve().parent.parent
        self.download_root = model_root or (self.base_dir / "voice" / "models" / "whisper")
        self.model_name = "tiny.en"
        self.device = "cpu"
        self.compute_type = "int8"

        # Model state (lazy loaded)
        self._model = None
        self._load_lock = threading.Lock()
        self.is_loaded = False
        self.load_time_sec = 0.0

        # Audio stream state
        self.sample_rate = 16000  # Target rate for Faster-Whisper
        self.capture_sample_rate = 16000  # Device native rate
        self.capture_channels = 1
        self.is_recording = False
        self._audio_chunks = []
        self._stream = None
        self._stream_lock = threading.Lock()
        self._start_time = 0.0

    def _ensure_loaded(self) -> bool:
        """Lazy-load the Faster-Whisper model into memory on demand."""
        if self.is_loaded and self._model is not None:
            return True

        with self._load_lock:
            if self.is_loaded and self._model is not None:
                return True
            try:
                from faster_whisper import WhisperModel
                logger.info(f"Loading Faster-Whisper ({self.model_name}) from {self.download_root}...")
                t0 = time.time()
                self._model = WhisperModel(
                    self.model_name,
                    device=self.device,
                    compute_type=self.compute_type,
                    download_root=str(self.download_root)
                )
                self.load_time_sec = round(time.time() - t0, 2)
                self.is_loaded = True
                logger.info(f"Faster-Whisper loaded in {self.load_time_sec}s.")
                return True
            except Exception as e:
                logger.error(f"Failed to load Faster-Whisper model: {e}")
                self._model = None
                self.is_loaded = False
                return False

    def is_mic_available(self) -> Tuple[bool, str]:
        """Check if an input recording device exists."""
        try:
            devices = sd.query_devices()
            input_devs = [d for d in devices if d.get('max_input_channels', 0) > 0]
            if not input_devs:
                return False, "No microphone input devices detected."
            default_in = sd.default.device[0]
            dev_name = devices[default_in]['name'] if default_in is not None and default_in < len(devices) else input_devs[0]['name']
            return True, dev_name
        except Exception as e:
            return False, str(e)

    def _audio_callback(self, indata, frames, time_info, status):
        """Streaming callback receiving microphone buffer chunks."""
        if status:
            logger.debug(f"Sounddevice status: {status}")
        if self.is_recording:
            self._audio_chunks.append(indata.copy())

    def start_recording(self) -> Dict[str, Any]:
        """Start capturing audio from the default microphone into memory."""
        with self._stream_lock:
            if self.is_recording:
                return {"status": "already_recording"}

            # Check mic availability
            avail, dev_info = self.is_mic_available()
            if not avail:
                return {"status": "error", "message": f"Microphone unavailable: {dev_info}"}

            try:
                self._audio_chunks = []
                self.is_recording = True
                self._start_time = time.time()

                # Determine hardware native sample rate & channels to avoid driver attenuation
                default_in = sd.default.device[0]
                dev = sd.query_devices(default_in)
                self.capture_sample_rate = int(dev.get('default_samplerate', 16000))
                self.capture_channels = min(2, dev.get('max_input_channels', 1))

                self._stream = sd.InputStream(
                    device=default_in,
                    samplerate=self.capture_sample_rate,
                    channels=self.capture_channels,
                    dtype="float32",
                    callback=self._audio_callback
                )
                self._stream.start()
                return {"status": "listening", "device": dev_info}
            except Exception as e:
                self.is_recording = False
                logger.error(f"Failed to start audio stream: {e}")
                return {"status": "error", "message": str(e)}

    def stop_recording(self) -> Dict[str, Any]:
        """Stop microphone capture and transcribe recorded buffer in memory."""
        with self._stream_lock:
            if not self.is_recording:
                return {"status": "not_recording", "text": ""}

            self.is_recording = False
            duration = time.time() - self._start_time

            try:
                if self._stream:
                    self._stream.stop()
                    self._stream.close()
                    self._stream = None
            except Exception as e:
                logger.warning(f"Error closing stream: {e}")

            # Assemble recorded chunks
            if not self._audio_chunks:
                return {"status": "empty", "text": "", "message": "No audio captured."}

            try:
                audio_raw = np.concatenate(self._audio_chunks, axis=0)
            except Exception as e:
                return {"status": "error", "text": "", "message": f"Buffer error: {e}"}
            finally:
                # Immediately purge raw chunks from memory
                self._audio_chunks = []

            # Convert multi-channel audio to mono
            if audio_raw.ndim > 1 and audio_raw.shape[1] > 1:
                audio_mono = np.mean(audio_raw, axis=1)
            else:
                audio_mono = audio_raw.flatten()

            # Resample in-memory to 16,000 Hz if recorded at hardware native rate (e.g. 44100 or 48000 Hz)
            if self.capture_sample_rate != self.sample_rate and len(audio_mono) > 0:
                target_len = int(len(audio_mono) * self.sample_rate / self.capture_sample_rate)
                audio_data = np.interp(
                    np.linspace(0, len(audio_mono), target_len, endpoint=False),
                    np.arange(len(audio_mono)),
                    audio_mono
                ).astype(np.float32)
            else:
                audio_data = audio_mono.astype(np.float32)

            # Check minimum duration and amplitude
            duration_captured = len(audio_data) / self.sample_rate
            if duration < 0.4 or duration_captured < 0.3:
                return {"status": "too_short", "text": "", "message": "Recording too short."}

            max_amp = float(np.max(np.abs(audio_data)))
            # Only reject if virtually zero (hardware disconnected or totally dead signal)
            if max_amp < 1e-4:
                return {"status": "silent", "text": "", "message": "Audio silent / no speech detected."}

            # Normalize audio amplitude so Faster-Whisper receives optimal dynamic range
            audio_data = (audio_data / max_amp) * 0.90

            # Ensure model is ready
            if not self._ensure_loaded():
                return {"status": "error", "text": "", "message": "Whisper model failed to load."}

            # Transcribe in-memory numpy array
            try:
                t0 = time.time()
                segments, info = self._model.transcribe(
                    audio_data,
                    beam_size=1,
                    language="en",
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=400)
                )

                text_parts = [segment.text.strip() for segment in segments]
                recognized_text = " ".join(text_parts).strip()
                transcribe_time = round(time.time() - t0, 2)

                if not recognized_text:
                    return {
                        "status": "unrecognized",
                        "text": "",
                        "duration": round(duration, 2),
                        "transcribe_time": transcribe_time
                    }

                return {
                    "status": "recognized",
                    "text": recognized_text,
                    "duration": round(duration, 2),
                    "transcribe_time": transcribe_time,
                    "confidence": round(info.language_probability, 2)
                }

            except Exception as e:
                logger.error(f"Transcription error: {e}")
                return {"status": "error", "text": "", "message": str(e)}

    def cancel_recording(self) -> Dict[str, str]:
        """Discard active recording immediately."""
        with self._stream_lock:
            self.is_recording = False
            try:
                if self._stream:
                    self._stream.stop()
                    self._stream.close()
                    self._stream = None
            except Exception:
                pass
            self._audio_chunks = []
            return {"status": "cancelled"}

    def status(self) -> Dict[str, Any]:
        """Return operational telemetry of the STT engine."""
        avail, dev_name = self.is_mic_available()
        return {
            "engine": "Faster-Whisper (Offline)",
            "model": self.model_name,
            "device": self.device,
            "compute_type": self.compute_type,
            "is_loaded": self.is_loaded,
            "is_recording": self.is_recording,
            "mic_available": avail,
            "mic_device": dev_name
        }
