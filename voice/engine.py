"""
E.D.I.T.H. Voice Engine Interface (Milestone 2 Stubs)
Designed for lightweight offline Whisper (STT) and Piper/Edge-TTS.
"""
from typing import Optional, Callable

class VoiceEngine:
    def __init__(self):
        self.is_listening = False
        self.tts_provider = "edge-tts"  # default target for M2
        self.stt_provider = "whisper-base"

    def status(self) -> dict:
        return {
            "stt_ready": False,
            "tts_ready": False,
            "milestone": "Scheduled for Milestone 2",
            "is_listening": self.is_listening
        }

    def speak(self, text: str, callback: Optional[Callable] = None):
        """Placeholder for speech synthesis."""
        # Milestone 2 implementation hook
        pass

    def start_listening(self, callback: Optional[Callable[[str], None]] = None):
        """Placeholder for voice activity detection & STT."""
        self.is_listening = True

    def stop_listening(self):
        self.is_listening = False
