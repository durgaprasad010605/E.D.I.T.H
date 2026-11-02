"""
E.D.I.T.H. Assistant Orchestrator & PyWebView Bridge API
Connects Python backend services to the JavaScript UI via PyWebView's native bridge.
"""
import datetime
from typing import Dict, Any, List
from .config import DB_PATH, DEFAULT_SETTINGS, VERSION, APP_NAME
from .system_monitor import SystemMonitor
from brain.mock_brain import MockBrain
from memory.database import DatabaseManager

class AssistantBridge:
    """
    Exposed directly to window.pywebview.api in JavaScript.
    All methods can be called asynchronously from the HUD.
    """

    def __init__(self):
        self.db = DatabaseManager(DB_PATH)
        self.telemetry_monitor = SystemMonitor()
        self.brain = MockBrain()
        self.settings = DEFAULT_SETTINGS.copy()
        self._load_saved_settings()

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

    def get_system_info(self) -> Dict[str, Any]:
        """Return application metadata and operational state."""
        return {
            "app_name": APP_NAME,
            "version": VERSION,
            "brain_engine": self.brain.get_name(),
            "mode": "LOCAL_OFFLINE",
            "security": "LEVEL_1_ALPHA"
        }

    def get_telemetry(self) -> Dict[str, Any]:
        """Fetch current hardware and OS metrics."""
        return self.telemetry_monitor.get_telemetry()

    def get_history(self) -> List[Dict[str, Any]]:
        """Fetch saved conversation messages."""
        return self.db.get_recent_messages(limit=50)

    def clear_history(self) -> Dict[str, bool]:
        """Clear conversation logs."""
        self.db.clear_messages()
        self.db.log_audit("INFO", "USER_CLEAR_HISTORY", "User cleared conversation history")
        return {"success": True}

    def send_message(self, text: str) -> Dict[str, Any]:
        """
        Process user prompt, generate EDITH response, and persist both.
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
            "user_callsign": self.settings.get("user_callsign", "Boss")
        }

        # 3. Check for in-app commands
        if text.lower() == "clear":
            self.db.clear_messages()
            return {
                "reply": "Display buffer and session logs cleared, Boss.",
                "timestamp": datetime.datetime.now().strftime("%I:%M %p"),
                "sender": "EDITH",
                "action": "clear_ui"
            }

        # 4. Generate intelligent in-character response
        reply = self.brain.generate_response(text, context)

        # 5. Save EDITH reply to local memory
        self.db.log_message("EDITH", reply)
        self.db.log_audit("INFO", "INTERACTION", f"Prompt length: {len(text)}")

        return {
            "reply": reply,
            "timestamp": datetime.datetime.now().strftime("%I:%M %p"),
            "sender": "EDITH",
            "action": "reply"
        }

    def get_settings(self) -> Dict[str, Any]:
        """Retrieve user configuration."""
        return self.settings

    def save_setting(self, key: str, value: Any) -> Dict[str, bool]:
        """Persist a user configuration option."""
        self.settings[key] = value
        self.db.set_setting(key, str(value))
        return {"success": True}
