"""
E.D.I.T.H. - Even Dead, I'm The Hero
Milestone 1 Desktop Application Entrypoint
Powered by Python, PyWebView (Edge WebView2), and Local SQLite
"""
import sys
import os
import webview
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.assistant import AssistantBridge
from core.config import (
    APP_NAME,
    APP_FULL_NAME,
    VERSION,
    UI_DIR,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_MIN_HEIGHT
)

def launch_edith():
    """Initialize the backend bridge and start the PyWebView desktop window."""
    print("=" * 60)
    print(f" Initializing {APP_NAME} ({APP_FULL_NAME}) - v{VERSION}")
    print(" Architecture: Local Modular Desktop HUD (Milestone 1)")
    print(" Privacy: 100% Localhost Isolated | Zero Cloud APIs")
    print("=" * 60)

    # 1. Initialize Assistant Bridge (Orchestrator)
    bridge_api = AssistantBridge()

    # 2. Path to the HTML entrypoint
    index_html = UI_DIR / "index.html"
    if not index_html.exists():
        raise FileNotFoundError(f"UI template not found at: {index_html}")

    # 3. Create Desktop Window using Windows native WebView2
    window = webview.create_window(
        title=f"{APP_NAME} // {APP_FULL_NAME}",
        url=str(index_html.as_uri()),
        js_api=bridge_api,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        min_size=(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT),
        resizable=True,
        background_color="#030712",
        text_select=False,
        confirm_close=False
    )

    # 4. Start PyWebView loop (Windows GUI thread)
    print("[+] EDITH HUD Window Active. Engaging desktop session...")
    webview.start(debug=False)
    print("[*] EDITH session safely terminated.")

if __name__ == "__main__":
    launch_edith()
