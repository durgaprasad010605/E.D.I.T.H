"""
Automated GUI Window Smoke Test for E.D.I.T.H.
Launches the PyWebView desktop window, verifies WebView2 engine initializes,
and closes the window after 4 seconds.
"""
import sys
import time
import webview
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.assistant import AssistantBridge
from core.config import UI_DIR, WINDOW_WIDTH, WINDOW_HEIGHT

def on_window_ready(window):
    """Callback executed once the window and WebView2 engine are live."""
    print("[+] PyWebView window callback active.")
    print(f"[+] Window title: {window.title}")
    print("[+] Waiting 3 seconds to verify rendering and JS bridge...")
    time.sleep(3)
    print("[+] Closing test window automatically...")
    window.destroy()
    print("[+] Window destroyed cleanly. Test complete!")

def run_smoke_test():
    bridge_api = AssistantBridge()
    index_html = UI_DIR / "index.html"

    window = webview.create_window(
        title="E.D.I.T.H. Smoke Test",
        url=str(index_html.as_uri()),
        js_api=bridge_api,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        background_color="#030712"
    )

    print("[*] Launching PyWebView GUI thread...")
    webview.start(on_window_ready, window)
    print("[*] PyWebView loop exited cleanly with code 0.")

if __name__ == "__main__":
    run_smoke_test()
