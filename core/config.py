"""
E.D.I.T.H. Configuration & System Constants
"""
import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UI_DIR = BASE_DIR / "ui"
DB_PATH = DATA_DIR / "edith.db"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

# App Metadata
APP_NAME = "E.D.I.T.H."
APP_FULL_NAME = "Even Dead, I'm The Hero"
VERSION = "1.0.0-M1"
DEVELOPER_TAG = "Stark Secure Systems"

# UI Settings
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
WINDOW_MIN_WIDTH = 960
WINDOW_MIN_HEIGHT = 650

# Default System Preferences
DEFAULT_SETTINGS = {
    "theme": "cyan",  # cyan, amber, stealth
    "voice_enabled": False,  # Ready for Milestone 2
    "voice_speed": 1.0,
    "sound_effects": True,
    "telemetry_interval_sec": 2,
    "user_callsign": "Boss"
}
