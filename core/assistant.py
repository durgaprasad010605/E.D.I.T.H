"""
E.D.I.T.H. Assistant Orchestrator & PyWebView Bridge API
Connects Python backend services to the JavaScript UI via PyWebView's native bridge.
Includes Milestone 2A Piper TTS voice output and Milestone 2B Faster-Whisper voice input.
"""
import json
import datetime
from typing import Dict, Any, List, Optional
from .config import DB_PATH, DEFAULT_SETTINGS, VERSION, APP_NAME
from .system_monitor import SystemMonitor
from brain.mock_brain import MockBrain
from memory.database import DatabaseManager
from voice.engine import VoiceEngine
from voice.stt import SpeechRecognizer
from voice.wake_word import WakeWordService, WakeWordState
from core.app_launcher import AppLauncher
from core.web_launcher import WebLauncher
from core.file_search import FileSearchEngine

class AssistantBridge:
    """
    Exposed directly to window.pywebview.api in JavaScript.
    All methods can be called asynchronously from the HUD.
    Includes Milestone 4.4 Local Wake Word ('Hey EDITH') & Hands-Free Voice Activation.
    """

    def __init__(self):
        self.db = DatabaseManager(DB_PATH)
        self.telemetry_monitor = SystemMonitor()
        self.launcher = AppLauncher(db=self.db)
        self.web_launcher = WebLauncher(db=self.db)
        self.file_search = FileSearchEngine(db=self.db)
        self.brain = MockBrain(
            db=self.db,
            launcher=self.launcher,
            web_launcher=self.web_launcher,
            file_search=self.file_search
        )
        self.voice = VoiceEngine()
        self.stt = SpeechRecognizer()
        self.settings = DEFAULT_SETTINGS.copy()
        self._load_saved_settings()

        # Synchronize voice mute state from saved settings
        is_muted = self.settings.get("voice_muted", False)
        if isinstance(is_muted, str):
            is_muted = is_muted.lower() in ("true", "1")
        self.voice.set_muted(bool(is_muted))

        # UI Window reference for direct JS push (Milestone 4.4)
        self.window = None
        self.current_hud_state = WakeWordState.STANDBY
        self.current_hud_details = "Waiting for 'Hey EDITH'"

        # Milestone 4.4 Local Wake Word & Hands-Free Service
        wake_enabled = self.settings.get("wake_word_enabled", True)
        if isinstance(wake_enabled, str):
            wake_enabled = wake_enabled.lower() in ("true", "1")
        silence_dur = float(self.settings.get("vad_silence_duration", 1.5))
        max_dur = float(self.settings.get("max_recording_duration", 15.0))

        self.wake_word = WakeWordService(
            stt_recognizer=self.stt,
            voice_engine=self.voice,
            on_state_change=self._on_hud_state_change,
            on_command_recognized=self._on_wake_command_recognized,
            silence_duration_sec=silence_dur,
            max_recording_duration_sec=max_dur,
            enabled=bool(wake_enabled)
        )

    def _load_saved_settings(self):
        """Restore user settings from local SQLite storage."""
        for key in self.settings.keys():
            saved = self.db.get_setting(key)
            if saved is not None:
                if isinstance(self.settings[key], bool):
                    self.settings[key] = saved.lower() in ("true", "1")
                elif isinstance(self.settings[key], (int, float)):
                    self.settings[key] = float(saved)
                else:
                    self.settings[key] = saved

    def set_window(self, window):
        """Bind PyWebView window reference for direct event dispatching."""
        self.window = window
        if hasattr(self, 'wake_word') and self.wake_word:
            self.wake_word.set_window(window)

    def set_hud_state(self, state_name: str, details: str = ""):
        """Update HUD state and broadcast to JavaScript UI."""
        self.current_hud_state = state_name
        self.current_hud_details = details
        if self.window:
            try:
                safe_s = state_name.replace("'", "\\'")
                safe_d = details.replace("'", "\\'")
                self.window.evaluate_js(
                    f"window.onEdithStateChange && window.onEdithStateChange('{safe_s}', '{safe_d}')"
                )
            except Exception:
                pass

    def _on_hud_state_change(self, new_state: str, details: str = ""):
        """Internal callback invoked when WakeWordService state shifts."""
        self.current_hud_state = new_state
        self.current_hud_details = details

    def _on_wake_command_recognized(self, text: str):
        """
        Executed when a hands-free directive is recognized after 'Hey EDITH'.
        Executes command through existing assistant pipeline and sends event to UI.
        """
        result = self.send_message(text)
        if self.window:
            try:
                # Push recognized interaction directly to communications console
                u_json = json.dumps(text)
                r_json = json.dumps(result)
                self.window.evaluate_js(
                    f"window.onHandsFreeInteraction && window.onHandsFreeInteraction({u_json}, {r_json})"
                )
            except Exception as e:
                pass

    def get_system_info(self) -> Dict[str, Any]:
        """Return application metadata and operational state."""
        stt_stat = self.stt.status()
        ww_stat = self.wake_word.status() if hasattr(self, 'wake_word') and self.wake_word else {}
        return {
            "app_name": APP_NAME,
            "version": VERSION,
            "brain_engine": self.brain.get_name(),
            "voice_engine": self.voice.status()["engine"],
            "voice_model": self.voice.status()["model"],
            "voice_muted": self.voice.is_muted,
            "stt_engine": stt_stat["engine"],
            "stt_model": stt_stat["model"],
            "mic_available": stt_stat["mic_available"],
            "mic_device": stt_stat["mic_device"],
            "wake_word_engine": ww_stat.get("engine", "Offline VAD + Whisper Spotter"),
            "wake_word": ww_stat.get("wake_word", "Hey EDITH"),
            "wake_word_enabled": self.wake_word.is_enabled if hasattr(self, 'wake_word') else False,
            "vad_silence_duration": self.wake_word.silence_duration_sec if hasattr(self, 'wake_word') else 1.5,
            "hud_state": self.current_hud_state,
            "approved_apps": [a["name"] for a in self.launcher.get_approved_apps()],
            "approved_websites": [w["name"] for w in self.web_launcher.get_approved_websites()],
            "search_roots": list(self.file_search.approved_roots.keys()),
            "mode": "LOCAL_OFFLINE",
            "security": "LEVEL_1_ALPHA"
        }

    def get_telemetry(self) -> Dict[str, Any]:
        """Fetch current hardware and OS metrics alongside voice state."""
        data = self.telemetry_monitor.get_telemetry()
        data["hud_state"] = self.current_hud_state
        data["hud_details"] = self.current_hud_details
        data["wake_word_enabled"] = self.wake_word.is_enabled if hasattr(self, 'wake_word') else False
        data["is_speaking"] = self.voice.is_speaking
        data["is_recording"] = self.stt.is_recording or (
            self.wake_word.is_recording_command if hasattr(self, 'wake_word') else False
        )
        return data

    def get_history(self) -> List[Dict[str, Any]]:
        """Fetch saved conversation messages."""
        return self.db.get_recent_messages(limit=50)

    def clear_history(self) -> Dict[str, bool]:
        """Clear conversation logs."""
        self.db.clear_messages()
        self.voice.stop()
        self.db.log_audit("INFO", "USER_CLEAR_HISTORY", "User cleared conversation history")
        return {"success": True}

    def send_message(self, text: str) -> Dict[str, Any]:
        """
        Process user prompt, generate EDITH response, speak it aloud via Piper TTS,
        and persist both in local memory.
        """
        text = text.strip()
        if not text:
            return {"error": "Empty message"}

        # 1. Save user message to local memory
        self.db.log_message("USER", text)

        # 2. Gather context for brain
        current_telemetry = self.telemetry_monitor.get_telemetry()
        context = {
            "telemetry": current_telemetry,
            "user_callsign": self.settings.get("user_callsign", "Boss"),
            "db": self.db,
            "launcher": self.launcher,
            "web_launcher": self.web_launcher,
            "file_search": self.file_search
        }

        # 3. Check for in-app commands
        if text.lower() == "clear":
            self.db.clear_messages()
            self.voice.stop()
            clear_msg = "Display buffer and session logs cleared, Boss."
            self.voice.speak(clear_msg)
            return {
                "reply": clear_msg,
                "timestamp": datetime.datetime.now().strftime("%I:%M %p"),
                "sender": "EDITH",
                "action": "clear_ui"
            }

        # 4. Generate intelligent in-character response
        reply = self.brain.generate_response(text, context)

        # 5. Save EDITH reply to local memory
        self.db.log_message("EDITH", reply)
        self.db.log_audit("INFO", "INTERACTION", f"Prompt length: {len(text)}")

        # 6. Speak the response aloud non-blockingly via Piper TTS (Milestone 2A)
        self.set_hud_state(WakeWordState.SPEAKING, "EDITH responding aloud")
        self.voice.speak(
            reply,
            callback=lambda: self.set_hud_state(WakeWordState.STANDBY, "Waiting for 'Hey EDITH'")
        )

        return {
            "reply": reply,
            "timestamp": datetime.datetime.now().strftime("%I:%M %p"),
            "sender": "EDITH",
            "action": "reply",
            "voice_muted": self.voice.is_muted
        }

    # ============================================================
    # MICROPHONE & SPEECH-TO-TEXT METHODS (Milestone 2B / 4.4 Fallback)
    # ============================================================
    def start_mic(self) -> Dict[str, Any]:
        """Activate microphone recording manually (fallback)."""
        # Stop any active TTS audio so microphone doesn't pick up EDITH's voice
        self.voice.stop()
        if hasattr(self, 'wake_word') and self.wake_word:
            self.wake_word.pause_for_manual_recording()
        self.set_hud_state(WakeWordState.LISTENING, "Manual recording active")
        return self.stt.start_recording()

    def stop_mic(self) -> Dict[str, Any]:
        """Stop microphone recording and transcribe captured audio in memory."""
        self.set_hud_state(WakeWordState.PROCESSING, "Transcribing manual recording")
        result = self.stt.stop_recording()
        if hasattr(self, 'wake_word') and self.wake_word:
            self.wake_word.resume_after_manual_recording()
        self.set_hud_state(WakeWordState.STANDBY, "Waiting for 'Hey EDITH'")
        return result

    def cancel_mic(self) -> Dict[str, str]:
        """Cancel current microphone session."""
        result = self.stt.cancel_recording()
        if hasattr(self, 'wake_word') and self.wake_word:
            self.wake_word.resume_after_manual_recording()
        self.set_hud_state(WakeWordState.STANDBY, "Manual recording cancelled")
        return result

    def get_stt_status(self) -> Dict[str, Any]:
        """Return speech recognition and microphone status."""
        return self.stt.status()

    # ============================================================
    # WAKE WORD & HANDS-FREE VOICE METHODS (Milestone 4.4)
    # ============================================================
    def get_hud_status(self) -> Dict[str, Any]:
        """Return live HUD state and wake-word configuration."""
        return {
            "hud_state": self.current_hud_state,
            "hud_details": self.current_hud_details,
            "wake_word_enabled": self.wake_word.is_enabled if hasattr(self, 'wake_word') else False,
            "wake_word": self.settings.get("wake_word", "Hey EDITH"),
            "silence_duration": self.wake_word.silence_duration_sec if hasattr(self, 'wake_word') else 1.5,
            "is_speaking": self.voice.is_speaking,
            "is_recording": self.stt.is_recording or (
                self.wake_word.is_recording_command if hasattr(self, 'wake_word') else False
            )
        }

    def toggle_wake_word(self) -> Dict[str, Any]:
        """Toggle hands-free wake word listening state."""
        if not hasattr(self, 'wake_word') or not self.wake_word:
            return {"enabled": False}
        new_state = not self.wake_word.is_enabled
        self.wake_word.set_enabled(new_state)
        self.save_setting("wake_word_enabled", new_state)
        return {"enabled": new_state, "state": self.current_hud_state}

    def set_wake_word_enabled(self, enabled: bool) -> Dict[str, Any]:
        """Explicitly enable or disable wake-word detection."""
        if hasattr(self, 'wake_word') and self.wake_word:
            self.wake_word.set_enabled(bool(enabled))
            self.save_setting("wake_word_enabled", bool(enabled))
            return {"enabled": self.wake_word.is_enabled, "state": self.current_hud_state}
        return {"enabled": False}

    def set_vad_silence_duration(self, duration_sec: float) -> Dict[str, Any]:
        """Configure VAD continuous silence duration before auto-stopping recording."""
        val = float(duration_sec)
        if hasattr(self, 'wake_word') and self.wake_word:
            self.wake_word.set_silence_duration(val)
        self.save_setting("vad_silence_duration", val)
        return {"success": True, "silence_duration": val}

    def get_wake_word_status(self) -> Dict[str, Any]:
        """Return detailed wake-word service telemetry."""
        if hasattr(self, 'wake_word') and self.wake_word:
            return self.wake_word.status()
        return {"engine": "Unavailable", "is_enabled": False}

    def cleanup(self):
        """Clean shutdown of all voice and hardware resources."""
        if hasattr(self, 'wake_word') and self.wake_word:
            self.wake_word.shutdown()
        if hasattr(self, 'voice') and self.voice:
            self.voice.stop()

    # ============================================================
    # VOICE CONTROL BRIDGE METHODS (Milestone 2A)
    # ============================================================
    def toggle_mute(self) -> Dict[str, Any]:
        """Toggle audio mute state."""
        new_state = self.voice.toggle_mute()
        self.save_setting("voice_muted", new_state)
        return {"is_muted": new_state}

    def set_muted(self, muted: bool) -> Dict[str, Any]:
        """Explicitly set audio mute state."""
        self.voice.set_muted(muted)
        self.save_setting("voice_muted", muted)
        return {"is_muted": self.voice.is_muted}

    def test_voice(self, phrase: Optional[str] = None) -> Dict[str, Any]:
        """Trigger an instant voice test phrase."""
        self.voice.test_voice(phrase)
        return {"status": "testing", "is_muted": self.voice.is_muted}

    def stop_speech(self) -> Dict[str, bool]:
        """Stop any active speech."""
        self.voice.stop()
        return {"stopped": True}

    def get_voice_status(self) -> Dict[str, Any]:
        """Return detailed voice engine status."""
        return self.voice.status()

    # ============================================================
    # PERSONAL MEMORY BRIDGE METHODS (Milestone 3, Feature 2)
    # ============================================================
    def get_memories(self, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve stored personal memories."""
        return self.db.get_memories(search=search)

    def add_memory(self, content: str, category: str = "general") -> Dict[str, Any]:
        """Save a new memory entry."""
        from brain.mock_brain import check_sensitive_content
        sensitive_reason = check_sensitive_content(content)
        if sensitive_reason:
            return {
                "success": False,
                "error": f"Security Protocol Alert: Cannot store {sensitive_reason} in memory."
            }
        mem_id = self.db.add_memory(content, category)
        return {"success": True, "id": mem_id, "content": content}

    def update_memory(self, memory_id: int, content: str) -> Dict[str, bool]:
        """Update existing memory."""
        success = self.db.update_memory(int(memory_id), content)
        return {"success": success}

    def delete_memory(self, memory_id: int) -> Dict[str, bool]:
        """Delete saved memory."""
        success = self.db.delete_memory(int(memory_id))
        return {"success": success}

    # ============================================================
    # TASK MANAGEMENT BRIDGE METHODS (Milestone 3, Feature 3)
    # ============================================================
    def get_tasks(self, completed: Optional[bool] = None) -> List[Dict[str, Any]]:
        """Retrieve tasks list."""
        return self.db.get_tasks(completed=completed)

    def add_task(self, title: str, due_date: Optional[str] = None) -> Dict[str, Any]:
        """Register a new task."""
        task_id = self.db.add_task(title, due_date=due_date)
        return {"success": True, "id": task_id, "title": title, "due_date": due_date}

    def toggle_task(self, task_id: int, completed: bool) -> Dict[str, bool]:
        """Toggle task completion state."""
        success = self.db.complete_task(int(task_id), bool(completed))
        return {"success": success}

    def delete_task(self, task_id: int) -> Dict[str, bool]:
        """Delete task entry."""
        success = self.db.delete_task(int(task_id))
        return {"success": success}

    # ============================================================
    # REMINDERS BRIDGE METHODS (Milestone 3, Feature 4)
    # ============================================================
    def get_reminders(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """Fetch reminders list."""
        return self.db.get_reminders(active_only=active_only)

    def add_reminder(self, title: str, remind_at: str) -> Dict[str, Any]:
        """Set a scheduled reminder."""
        rem_id = self.db.add_reminder(title, remind_at)
        return {"success": True, "id": rem_id, "title": title, "remind_at": remind_at}

    def complete_reminder(self, reminder_id: int) -> Dict[str, bool]:
        """Dismiss/complete a reminder."""
        success = self.db.complete_reminder(int(reminder_id), completed=True)
        return {"success": success}

    def delete_reminder(self, reminder_id: int) -> Dict[str, bool]:
        """Delete a reminder."""
        success = self.db.delete_reminder(int(reminder_id))
        return {"success": success}

    def check_due_reminders(self) -> List[Dict[str, Any]]:
        """Check for reminders whose time has arrived and flag them as notified."""
        due = self.db.get_due_reminders()
        for r in due:
            self.db.mark_reminder_notified(r["id"])
        return due

    # ============================================================
    # SETTINGS METHODS
    # ============================================================
    def get_settings(self) -> Dict[str, Any]:
        """Retrieve user configuration."""
        self.settings["voice_muted"] = self.voice.is_muted
        return self.settings

    def save_setting(self, key: str, value: Any) -> Dict[str, bool]:
        """Persist a user configuration option."""
        self.settings[key] = value
        self.db.set_setting(key, str(value))
        if key == "voice_muted":
            self.voice.set_muted(bool(value))
        elif key == "wake_word_enabled":
            if hasattr(self, 'wake_word') and self.wake_word:
                bool_val = value.lower() in ("true", "1") if isinstance(value, str) else bool(value)
                self.wake_word.set_enabled(bool_val)
        elif key == "vad_silence_duration":
            if hasattr(self, 'wake_word') and self.wake_word:
                self.wake_word.set_silence_duration(float(value))
        return {"success": True}

    # ============================================================
    # APPLICATION LAUNCHER BRIDGE METHODS (Milestone 4.1)
    # ============================================================
    def get_approved_apps(self) -> List[Dict[str, str]]:
        """Return the list of approved applications."""
        return self.launcher.get_approved_apps()

    def launch_app(self, app_id_or_name: str) -> Dict[str, Any]:
        """Safely launch an approved application by alias or ID."""
        matched = self.launcher.match_app(app_id_or_name)
        if not matched:
            return {
                "success": False,
                "error": f"Security Notice: '{app_id_or_name}' is not in the approved application allowlist."
            }
        return self.launcher.launch_app(matched)

    # ============================================================
    # WEBSITE LAUNCHER BRIDGE METHODS (Milestone 4.2)
    # ============================================================
    def get_approved_websites(self) -> List[Dict[str, str]]:
        """Return the list of approved websites."""
        return self.web_launcher.get_approved_websites()

    def launch_website(self, site_id_or_name: str) -> Dict[str, Any]:
        """Safely open an approved website by alias or ID in default browser."""
        matched = self.web_launcher.match_website(site_id_or_name)
        if not matched:
            return {
                "success": False,
                "error": f"Security Notice: '{site_id_or_name}' is not in the approved website allowlist."
            }
        return self.web_launcher.launch_website(matched)

    # ============================================================
    # SAFE LOCAL FILE SEARCH BRIDGE METHODS (Milestone 4.3)
    # ============================================================
    def search_files(self, query: str, scope: Optional[str] = None, target_type: str = "any") -> Dict[str, Any]:
        """Execute safe read-only local search."""
        parsed = self.file_search.parse_query(f"find {query}")
        kw = parsed.get("keyword") if parsed else query
        ext = parsed.get("extension") if parsed else None
        tt = parsed.get("target_type") if parsed else target_type
        sc = parsed.get("scope") if parsed else scope
        results = self.file_search.search(keyword=kw, extension=ext, target_type=tt, scope=sc)
        items, start_idx, end_idx, total = self.file_search.get_current_page_results()
        return {
            "items": items,
            "start": start_idx,
            "end": end_idx,
            "total": total,
            "page": self.file_search.current_page
        }

    def open_search_result(self, index: int, open_folder: bool = False) -> Dict[str, Any]:
        """Open a search result file or folder."""
        callsign = self.settings.get("user_callsign", "Boss")
        success, msg = self.file_search.open_result(int(index), open_folder=bool(open_folder), callsign=callsign)
        return {"success": success, "message": msg}

    def get_next_search_page(self) -> Dict[str, Any]:
        """Fetch the next page of search results."""
        callsign = self.settings.get("user_callsign", "Boss")
        msg = self.file_search.next_page(callsign)
        items, start_idx, end_idx, total = self.file_search.get_current_page_results()
        return {
            "items": items,
            "start": start_idx,
            "end": end_idx,
            "total": total,
            "page": self.file_search.current_page,
            "message": msg
        }



