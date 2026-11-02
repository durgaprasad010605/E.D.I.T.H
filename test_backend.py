"""
Automated Backend & Bridge Test Suite for E.D.I.T.H. Milestone 1
Verifies database integrity, mock brain responses, telemetry, and settings.
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.assistant import AssistantBridge

def run_tests():
    print(">>> Running EDITH Milestone 1 Backend Verification Suite...")
    bridge = AssistantBridge()

    # 1. Test System Info
    info = bridge.get_system_info()
    print(f"[TEST 1] System Info: {info['app_name']} v{info['version']} ({info['brain_engine']})")
    assert info['app_name'] == "E.D.I.T.H."
    assert "Mock" in info['brain_engine']

    # 2. Test Telemetry
    tele = bridge.get_telemetry()
    print(f"[TEST 2] Telemetry: CPU={tele['cpu_percent']}%, RAM={tele['ram_used_gb']}GB / {tele['ram_total_gb']}GB, OS={tele['os']}")
    assert "cpu_percent" in tele
    assert "ram_percent" in tele
    assert tele["ram_total_gb"] > 0

    # 3. Test Messages & In-character Brain
    test_queries = [
        "Hello EDITH",
        "Who are you?",
        "Status report",
        "What time is it?",
        "What is your security protocol?"
    ]

    for q in test_queries:
        res = bridge.send_message(q)
        print(f"[TEST 3] User: '{q}' -> EDITH ({res['timestamp']}): {res['reply'][:60]}...")
        assert "reply" in res
        assert len(res["reply"]) > 5

    # 4. Test History Persistence
    history = bridge.get_history()
    print(f"[TEST 4] History stored: {len(history)} messages in SQLite")
    assert len(history) >= len(test_queries) * 2

    # 5. Test Settings Persistence
    bridge.save_setting("user_callsign", "Tony")
    settings = bridge.get_settings()
    print(f"[TEST 5] Settings verified: Callsign = {settings.get('user_callsign')}")
    assert settings.get("user_callsign") == "Tony"

    # Restore default callsign
    bridge.save_setting("user_callsign", "Boss")

    print("\n>>> ALL MILESTONE 1 BACKEND TESTS PASSED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    run_tests()
