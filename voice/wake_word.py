"""
E.D.I.T.H. Local Wake Word & Hands-Free Voice Activation Engine (Milestone 4.4)
100% Offline, Local, Low-Resource Wake-Word & VAD System.
- Wake Word: "Hey EDITH"
- Local Voice Activity Detection (VAD): Silero VAD ONNX + Adaptive Energy Gate
- Speech-End Silence Detection (Configurable, default 1.5s)
- Model Reuse: Reuses existing Faster-Whisper tiny.en INT8 model (zero duplicate memory)
- Zero Disk Footprint: Audio buffers kept strictly in RAM and freed immediately
- Thread-Safe, Non-Blocking, Graceful Error Handling
"""
import io
import re
import math
import time
import wave
import queue
import struct
import logging
import threading
import collections
from typing import Optional, Callable, Dict, Any, List, Tuple
import numpy as np
import sounddevice as sd

try:
    import winsound
except ImportError:
    winsound = None

logger = logging.getLogger("EDITH.WakeWord")


class WakeWordState:
    """Official HUD states for Milestone 4.4."""
    STANDBY = "STANDBY"
    WAKE_WORD_DETECTED = "WAKE WORD DETECTED"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    SPEAKING = "SPEAKING"
    ERROR = "ERROR"


def generate_acknowledgement_chime(sample_rate: int = 22050) -> bytes:
    """
    Synthesize a clean, futuristic two-tone sci-fi activation chime in memory.
    Zero disk storage; pure in-memory WAV bytes.
    Tone 1: 784.0 Hz (G5) for 60ms
    Tone 2: 1046.5 Hz (C6) for 100ms
    """
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)

        dur1 = int(sample_rate * 0.06)
        dur2 = int(sample_rate * 0.10)

        # Tone 1 with exponential decay envelope
        t1 = [
            int(math.sin(2 * math.pi * 784.0 * t / sample_rate) * 14000 * math.exp(-t / (sample_rate * 0.05)))
            for t in range(dur1)
        ]
        # Tone 2 with exponential decay envelope
        t2 = [
            int(math.sin(2 * math.pi * 1046.5 * t / sample_rate) * 16000 * math.exp(-t / (sample_rate * 0.08)))
            for t in range(dur2)
        ]

        frames = b''.join(struct.pack('<h', max(-32768, min(32767, s))) for s in (t1 + t2))
        w.writeframes(frames)

    return buf.getvalue()


# Pre-cached acknowledgement sound bytes in memory
_ACK_SOUND_WAV: bytes = generate_acknowledgement_chime()


def play_acknowledgement_sound():
    """Play the in-memory acknowledgement chime asynchronously."""
    if winsound:
        try:
            winsound.PlaySound(_ACK_SOUND_WAV, winsound.SND_MEMORY | winsound.SND_ASYNC)
        except Exception as e:
            logger.debug(f"Audio chime notification notice: {e}")


class VoiceActivityDetector:
    """
    Ultra-lightweight two-stage Voice Activity Detector:
    Stage 1: RMS Energy Gate (<0.001ms CPU time, filters ambient silence/noise).
    Stage 2: Silero VAD v6 (ONNX Runtime, evaluates candidate speech frames with high precision).
    """

    def __init__(self, sample_rate: int = 16000, frame_size: int = 512):
        self.sample_rate = sample_rate
        self.frame_size = frame_size
        self._vad_model = None
        self._load_lock = threading.Lock()
        self.noise_floor = 0.005  # Adaptive RMS noise floor
        self.speech_prob_threshold = 0.45

    def _ensure_model(self):
        """Lazy load the Silero VAD ONNX model from faster_whisper assets."""
        if self._vad_model is not None:
            return self._vad_model
        with self._load_lock:
            if self._vad_model is not None:
                return self._vad_model
            try:
                from faster_whisper.vad import get_vad_model
                self._vad_model = get_vad_model()
            except Exception as e:
                logger.warning(f"Could not load Silero VAD model: {e}; falling back to pure energy VAD.")
                self._vad_model = None
            return self._vad_model

    def is_speech(self, frame: np.ndarray) -> bool:
        """
        Evaluate if a 16kHz float32 audio frame contains human speech.
        :param frame: 1D numpy array of length `frame_size` (512 samples = 32ms)
        """
        if frame is None or len(frame) == 0:
            return False

        # Ensure 1D float32
        if frame.ndim > 1:
            frame = frame.flatten()
        if frame.dtype != np.float32:
            frame = frame.astype(np.float32)

        # Stage 1: Energy gate
        rms = float(np.sqrt(np.mean(frame ** 2)))
        # Update adaptive noise floor slowly during low energy
        if rms < self.noise_floor:
            self.noise_floor = 0.98 * self.noise_floor + 0.02 * rms
        elif rms > 4.0 * self.noise_floor:
            # Significant energy above noise floor
            pass
        else:
            self.noise_floor = 0.995 * self.noise_floor + 0.005 * rms

        # If energy is below minimum audible gate, treat immediately as silence (<0.001ms CPU)
        if rms < max(0.003, self.noise_floor * 1.5):
            return False

        # Stage 2: Silero VAD model inference
        model = self._ensure_model()
        if model is not None:
            try:
                # Ensure frame length is exact multiple of 512
                if len(frame) != self.frame_size:
                    if len(frame) > self.frame_size:
                        eval_frame = frame[:self.frame_size]
                    else:
                        eval_frame = np.pad(frame, (0, self.frame_size - len(frame)))
                else:
                    eval_frame = frame

                prob = float(model(eval_frame)[0])
                return prob >= self.speech_prob_threshold
            except Exception as e:
                logger.debug(f"Silero VAD evaluation error: {e}")
                return rms > 0.02
        else:
            # Fallback to energy gate
            return rms > max(0.015, self.noise_floor * 2.5)


class WakeWordService:
    """
    Hands-free voice orchestrator for E.D.I.T.H.
    - Monitors microphone stream in background thread using local VAD and Whisper.
    - Detects wake phrase ("Hey EDITH" / "Edith").
    - Plays acknowledgement chime and begins recording automatically.
    - Uses local VAD to detect when user stops speaking (1.5s continuous silence).
    - Automatically stops recording, transcribes, and executes command via AssistantBridge.
    - Pauses during EDITH speech to prevent barge-in and audio feedback loop.
    - Releases microphone completely when disabled or on application shutdown.
    """

    def __init__(
        self,
        stt_recognizer,
        voice_engine,
        on_state_change: Optional[Callable[[str, str], None]] = None,
        on_command_recognized: Optional[Callable[[str], None]] = None,
        silence_duration_sec: float = 1.5,
        max_recording_duration_sec: float = 15.0,
        enabled: bool = True
    ):
        self.stt = stt_recognizer
        self.voice = voice_engine
        self.on_state_change = on_state_change
        self.on_command_recognized = on_command_recognized

        # Operational parameters
        self.silence_duration_sec = float(silence_duration_sec)
        self.max_recording_duration_sec = float(max_recording_duration_sec)
        self.is_enabled = bool(enabled)
        self.current_state = WakeWordState.STANDBY

        # Audio stream constants
        self.sample_rate = 16000
        self.frame_size = 512  # 32ms frames at 16kHz
        self.vad = VoiceActivityDetector(sample_rate=self.sample_rate, frame_size=self.frame_size)

        # Audio stream control
        self._running = False
        self._paused_for_manual = False
        self._thread: Optional[threading.Thread] = None
        self._stream: Optional[sd.InputStream] = None
        self._stream_lock = threading.Lock()
        self._audio_queue: queue.Queue = queue.Queue(maxsize=100)

        # Sliding audio ring buffer for wake word detection (keeps ~1.5s of audio)
        self.wake_buffer_max_samples = int(self.sample_rate * 1.6)
        self._ring_buffer = collections.deque(maxlen=self.wake_buffer_max_samples)

        # Speech burst tracking for wake word detection
        self._speech_in_progress = False
        self._speech_burst_samples = 0
        self._speech_silence_samples = 0

        # Command recording state
        self.is_recording_command = False
        self._command_audio_chunks: List[np.ndarray] = []
        self._command_has_speech = False
        self._command_continuous_silence_samples = 0
        self._command_total_samples = 0

        # UI Window handle (optional for direct evaluate_js push)
        self.window = None

        # Lock for state transitions
        self._state_lock = threading.Lock()

        # Start background monitor if enabled
        if self.is_enabled:
            self.start()

    def set_window(self, window):
        """Register PyWebView window handle for instant push state notifications."""
        self.window = window

    def _set_state(self, new_state: str, details: str = ""):
        """Update internal state and trigger listener callbacks."""
        with self._state_lock:
            self.current_state = new_state
            logger.info(f"EDITH State -> {new_state} {f'({details})' if details else ''}")

        if self.on_state_change:
            try:
                self.on_state_change(new_state, details)
            except Exception as e:
                logger.error(f"Error in on_state_change callback: {e}")

        # Direct PyWebView push if window is attached
        if self.window:
            try:
                safe_s = new_state.replace("'", "\\'")
                safe_d = details.replace("'", "\\'")
                self.window.evaluate_js(
                    f"window.onEdithStateChange && window.onEdithStateChange('{safe_s}', '{safe_d}')"
                )
            except Exception:
                pass

    def set_enabled(self, enabled: bool):
        """Enable or disable hands-free wake word detection."""
        if self.is_enabled == enabled:
            return

        self.is_enabled = enabled
        if self.is_enabled:
            logger.info("Enabling hands-free wake word detection...")
            self.start()
            self._set_state(WakeWordState.STANDBY, "Wake word enabled")
        else:
            logger.info("Disabling hands-free wake word detection. Releasing microphone...")
            self.stop()
            self._set_state(WakeWordState.STANDBY, "Wake word disabled")

    def set_silence_duration(self, duration_sec: float):
        """Configure continuous silence duration before auto-stopping recording."""
        self.silence_duration_sec = max(0.4, min(5.0, float(duration_sec)))
        logger.info(f"VAD silence duration updated to {self.silence_duration_sec}s")

    def set_max_duration(self, max_duration_sec: float):
        """Configure maximum recording duration."""
        self.max_recording_duration_sec = max(2.0, min(60.0, float(max_duration_sec)))

    def pause_for_manual_recording(self):
        """Pause wake word monitoring to yield the microphone to manual recording."""
        self._paused_for_manual = True
        self._close_stream()

    def resume_after_manual_recording(self):
        """Resume wake word monitoring after manual recording concludes."""
        self._paused_for_manual = False
        if self.is_enabled and not self._running:
            self.start()

    def _audio_callback(self, indata, frames, time_info, status):
        """Sounddevice streaming callback."""
        if status:
            logger.debug(f"Audio stream status: {status}")
        if self._running and not self._paused_for_manual:
            try:
                # Convert to mono float32
                if indata.ndim > 1 and indata.shape[1] > 1:
                    chunk = np.mean(indata, axis=1).astype(np.float32)
                else:
                    chunk = indata.flatten().astype(np.float32)
                self._audio_queue.put_nowait(chunk)
            except queue.Full:
                pass

    def start(self):
        """Start background microphone monitoring."""
        with self._stream_lock:
            if self._running:
                return

            # Check if microphone is available
            avail, dev_name = self.stt.is_mic_available()
            if not avail:
                logger.warning(f"Microphone unavailable for wake word: {dev_name}")
                self._set_state(WakeWordState.ERROR, "Microphone unavailable")
                return

            self._running = True
            self._speech_in_progress = False
            self._speech_burst_samples = 0
            self._ring_buffer.clear()

            try:
                self._stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype="float32",
                    blocksize=self.frame_size,
                    callback=self._audio_callback
                )
                self._stream.start()
                logger.info("Wake word audio stream opened successfully.")
            except Exception as e:
                self._running = False
                logger.error(f"Failed to open wake-word input stream: {e}")
                self._set_state(WakeWordState.ERROR, str(e))
                return

            self._thread = threading.Thread(target=self._monitor_worker, daemon=True)
            self._thread.start()
            self._set_state(WakeWordState.STANDBY, "Waiting for 'Hey EDITH'")

    def _close_stream(self):
        """Safely close sounddevice audio stream and release microphone device."""
        with self._stream_lock:
            if self._stream:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception as e:
                    logger.debug(f"Stream close notice: {e}")
                finally:
                    self._stream = None

    def stop(self):
        """Stop background worker and release microphone."""
        self._running = False
        self._close_stream()
        # Drain queue
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break
        if self._thread and self._thread.is_alive() and threading.current_thread() != self._thread:
            self._thread.join(timeout=1.0)
        self._thread = None
        logger.info("WakeWordService stopped cleanly.")

    def shutdown(self):
        """Complete application shutdown cleanup."""
        self.is_enabled = False
        self.stop()

    def feed_audio(self, audio_chunk: np.ndarray):
        """
        Inject audio frames directly into the processing pipeline.
        Used for automated unit testing without hardware microphone.
        """
        if audio_chunk is None:
            return
        if audio_chunk.ndim > 1:
            audio_chunk = audio_chunk.flatten()
        audio_chunk = audio_chunk.astype(np.float32)

        # Slice into frame_size chunks and process sequentially
        for i in range(0, len(audio_chunk), self.frame_size):
            chunk = audio_chunk[i:i + self.frame_size]
            if len(chunk) < self.frame_size:
                chunk = np.pad(chunk, (0, self.frame_size - len(chunk)))
            self._process_frame(chunk)

    def _process_frame(self, frame: np.ndarray):
        """
        Core state machine processing a single 16kHz float32 audio frame (512 samples = 32ms).
        """
        # Guard: If EDITH voice output is speaking, do not listen (barge-in / self-trigger protection)
        if self.voice and self.voice.is_speaking:
            if self.current_state != WakeWordState.SPEAKING:
                self._set_state(WakeWordState.SPEAKING, "EDITH responding aloud")
            # Clear speech detection buffers while speaking
            self._ring_buffer.clear()
            self._speech_in_progress = False
            return
        elif self.current_state == WakeWordState.SPEAKING and not (self.voice and self.voice.is_speaking):
            # Speech has concluded, transition back to STANDBY
            self._set_state(WakeWordState.STANDBY, "Waiting for 'Hey EDITH'")

        # VAD detection on current frame
        is_speech = self.vad.is_speech(frame)

        # ==============================================================
        # MODE 1: Active Hands-Free Command Recording Session
        # ==============================================================
        if self.is_recording_command:
            self._command_audio_chunks.append(frame.copy())
            self._command_total_samples += len(frame)

            if is_speech:
                self._command_has_speech = True
                self._command_continuous_silence_samples = 0
            else:
                if self._command_has_speech:
                    self._command_continuous_silence_samples += len(frame)
                else:
                    # Waiting for user to start speaking after wake sound
                    pass

            # Check 1: Continuous silence threshold reached after speech began (Speech End Detection)
            silence_samples_limit = int(self.silence_duration_sec * self.sample_rate)
            if self._command_has_speech and self._command_continuous_silence_samples >= silence_samples_limit:
                logger.info(f"VAD: Silence duration ({self.silence_duration_sec}s) reached. Stopping recording.")
                self._finish_command_recording()
                return

            # Check 2: Initial speech timeout (if user triggered wake word but never spoke a command)
            initial_silence_limit = int(4.5 * self.sample_rate)
            if not self._command_has_speech and self._command_total_samples >= initial_silence_limit:
                logger.info("VAD: No speech detected following wake word. Returning to STANDBY.")
                self.is_recording_command = False
                self._command_audio_chunks = []
                self._set_state(WakeWordState.STANDBY, "No speech detected")
                return

            # Check 3: Maximum recording duration safety limit
            max_samples_limit = int(self.max_recording_duration_sec * self.sample_rate)
            if self._command_total_samples >= max_samples_limit:
                logger.info("VAD: Maximum recording duration reached. Auto-stopping.")
                self._finish_command_recording()
                return

            return

        # ==============================================================
        # MODE 2: Wake Word Detection ("Hey EDITH" / "Edith")
        # ==============================================================
        self._ring_buffer.extend(frame)

        if is_speech:
            self._speech_in_progress = True
            self._speech_burst_samples += len(frame)
            self._speech_silence_samples = 0
        else:
            if self._speech_in_progress:
                self._speech_silence_samples += len(frame)

                # A short silence pause (~250ms) after speech or burst duration reached
                # signifies that a candidate phrase utterance has concluded
                pause_threshold = int(0.28 * self.sample_rate)
                min_burst_samples = int(0.40 * self.sample_rate)   # Minimum 400ms for "Edith"
                max_burst_samples = int(1.80 * self.sample_rate)   # Maximum 1.8s for "Hey EDITH"

                if self._speech_silence_samples >= pause_threshold:
                    if min_burst_samples <= self._speech_burst_samples <= max_burst_samples:
                        # Extract the candidate utterance window from the ring buffer
                        total_samples = self._speech_burst_samples + self._speech_silence_samples
                        samples_to_take = min(len(self._ring_buffer), total_samples + int(0.1 * self.sample_rate))
                        candidate_audio = np.array(list(self._ring_buffer)[-samples_to_take:], dtype=np.float32)

                        # Evaluate candidate utterance for wake word
                        self._evaluate_wake_phrase(candidate_audio)

                    # Reset burst tracking
                    self._speech_in_progress = False
                    self._speech_burst_samples = 0
                    self._speech_silence_samples = 0
            else:
                self._speech_burst_samples = 0
                self._speech_silence_samples = 0

    def _normalize_text(self, text: str) -> str:
        """Strip punctuation and normalize spacing."""
        cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower())
        return ' '.join(cleaned.split())

    def _evaluate_wake_phrase(self, audio: np.ndarray):
        """
        Verify if the candidate speech snippet matches the wake phrase.
        Reuses the existing Faster-Whisper tiny.en INT8 model (zero duplicate memory!).
        """
        if not self.stt:
            return

        # Ensure Whisper model is ready
        if not self.stt._ensure_loaded():
            return

        try:
            # Normalize amplitude for Whisper
            max_amp = float(np.max(np.abs(audio)))
            if max_amp < 1e-4:
                return
            norm_audio = (audio / max_amp) * 0.90

            # Transcribe the short 0.5s-1.5s snippet
            segments, _ = self.stt._model.transcribe(
                norm_audio,
                beam_size=1,
                language="en",
                vad_filter=False
            )
            raw_text = " ".join([s.text.strip() for s in segments]).strip()
            if not raw_text:
                return

            normalized = self._normalize_text(raw_text)
            logger.info(f"Wake candidate transcription: '{raw_text}' (normalized: '{normalized}')")

            # Check for wake phrase matches
            wake_match = False
            command_remainder = ""

            # Canonical wake triggers
            triggers = ["hey edith", "edith", "hey edit", "heyedith", "e d i t h"]

            for trigger in triggers:
                if normalized == trigger:
                    wake_match = True
                    command_remainder = ""
                    break
                elif normalized.startswith(trigger + " "):
                    wake_match = True
                    command_remainder = normalized[len(trigger):].strip()
                    break

            if wake_match:
                logger.info(f"*** WAKE WORD DETECTED: '{raw_text}' ***")
                self._trigger_wake_activated(command_remainder)
            else:
                logger.debug(f"Wake phrase rejected: '{normalized}' is not a wake word.")

        except Exception as e:
            logger.warning(f"Error evaluating wake phrase: {e}")

    def _trigger_wake_activated(self, inline_command: str = ""):
        """Handle wake-word activation sequence."""
        # 1. Update State to WAKE WORD DETECTED
        self._set_state(WakeWordState.WAKE_WORD_DETECTED, "Hey EDITH recognized")

        # 2. Play high-tech acknowledgement sound
        play_acknowledgement_sound()

        # If the user spoke the command in the same breath (e.g. "Hey EDITH what time is it"):
        if inline_command and len(inline_command) > 2:
            logger.info(f"Inline command detected with wake word: '{inline_command}'")
            self._set_state(WakeWordState.PROCESSING, f"Executing: {inline_command}")
            if self.on_command_recognized:
                threading.Thread(target=self.on_command_recognized, args=(inline_command,), daemon=True).start()
            return

        # 3. Transition to LISTENING mode to record user command automatically
        time.sleep(0.18)  # Let chime clear before recording
        self._ring_buffer.clear()
        self.is_recording_command = True
        self._command_audio_chunks = []
        self._command_has_speech = False
        self._command_continuous_silence_samples = 0
        self._command_total_samples = 0
        self._set_state(WakeWordState.LISTENING, "Recording user command hands-free")

    def _finish_command_recording(self):
        """Conclude hands-free recording session and transcribe in-memory buffer."""
        self.is_recording_command = False
        self._set_state(WakeWordState.PROCESSING, "Transcribing speech via Faster-Whisper")

        chunks = self._command_audio_chunks
        self._command_audio_chunks = []  # Release reference immediately

        if not chunks:
            self._set_state(WakeWordState.STANDBY, "No audio captured")
            return

        try:
            audio_raw = np.concatenate(chunks, axis=0)
        except Exception as e:
            logger.error(f"Error assembling audio chunks: {e}")
            self._set_state(WakeWordState.ERROR, "Buffer error")
            return

        duration = len(audio_raw) / self.sample_rate
        if duration < 0.4:
            self._set_state(WakeWordState.STANDBY, "Recording too short")
            return

        max_amp = float(np.max(np.abs(audio_raw)))
        if max_amp < 1e-4:
            self._set_state(WakeWordState.STANDBY, "Silent audio")
            return

        # Normalize in memory
        norm_audio = (audio_raw / max_amp) * 0.90

        # Transcribe in background thread to keep monitor thread responsive
        threading.Thread(target=self._transcribe_and_dispatch, args=(norm_audio,), daemon=True).start()

    def _transcribe_and_dispatch(self, audio_data: np.ndarray):
        """Transcribe recorded command audio and dispatch to assistant pipeline."""
        try:
            t0 = time.time()
            segments, info = self.stt._model.transcribe(
                audio_data,
                beam_size=1,
                language="en",
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=400)
            )
            text_parts = [segment.text.strip() for segment in segments]
            recognized_text = " ".join(text_parts).strip()
            latency = round(time.time() - t0, 2)

            if not recognized_text:
                logger.info("Speech unrecognized or empty.")
                self._set_state(WakeWordState.STANDBY, "Unrecognized directive")
                return

            logger.info(f"Hands-Free Directive Recognized in {latency}s: '{recognized_text}'")

            # Dispatch command to Assistant Bridge
            if self.on_command_recognized:
                self.on_command_recognized(recognized_text)

        except Exception as e:
            logger.error(f"Error transcribing hands-free command: {e}")
            self._set_state(WakeWordState.ERROR, str(e))
            time.sleep(1.5)
            self._set_state(WakeWordState.STANDBY, "Recovered")

    def _monitor_worker(self):
        """Background daemon processing incoming audio queue."""
        logger.info("WakeWord monitor worker started.")
        while self._running:
            try:
                chunk = self._audio_queue.get(timeout=0.1)
                self._process_frame(chunk)
                self._audio_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Unexpected error in wake-word worker: {e}")
                time.sleep(0.05)

        logger.info("WakeWord monitor worker exited.")

    def status(self) -> Dict[str, Any]:
        """Return operational telemetry."""
        avail, dev_name = self.stt.is_mic_available()
        return {
            "engine": "EDITH VAD & Whisper Keyword Spotter (Offline)",
            "wake_word": "Hey EDITH",
            "state": self.current_state,
            "is_enabled": self.is_enabled,
            "is_running": self._running,
            "is_recording_command": self.is_recording_command,
            "silence_duration_sec": self.silence_duration_sec,
            "max_recording_duration_sec": self.max_recording_duration_sec,
            "mic_available": avail,
            "mic_device": dev_name
        }
