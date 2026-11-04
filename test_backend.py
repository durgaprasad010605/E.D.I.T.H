"""
Automated Backend & Bridge Test Suite for E.D.I.T.H. (Milestones 1, 2A, 2B, 3, 4.1, 4.2, 4.3)
Verifies database integrity, mock brain responses, telemetry, settings,
Piper TTS voice, Faster-Whisper STT, Milestone 3 Persistent Memory & Tasks,
Milestone 4.1 App Launcher, Milestone 4.2 Web Launcher, and Milestone 4.3 Local File Search.
"""
import sys
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.assistant import AssistantBridge

def run_tests():
    print(">>> Running EDITH Milestone 1, 2A, 2B & 3 Verification Suite...")
    bridge = AssistantBridge()

    # 1. Test System Info
    info = bridge.get_system_info()
    print(f"[TEST 1] System Info: {info['app_name']} v{info['version']} ({info['brain_engine']})")
    assert info['app_name'] == "E.D.I.T.H."
    assert "Mock" in info['brain_engine']
    assert "Piper TTS" in info['voice_engine']
    assert "Faster-Whisper" in info['stt_engine']
    assert "4.4.0-M4.4" in info['version'] or "4.3.0-M4.3" in info['version']
    assert "approved_apps" in info
    assert len(info["approved_apps"]) == 5
    assert "approved_websites" in info
    assert len(info["approved_websites"]) == 8
    assert "search_roots" in info
    assert len(info["search_roots"]) >= 6

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
        print(f"[TEST 3] User: '{q}' -> EDITH: {res['reply'][:60]}...")
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
    bridge.save_setting("user_callsign", "Boss")

    # 6. Test Voice Engine Integration (Milestone 2A)
    voice_status = bridge.get_voice_status()
    print(f"[TEST 6] Voice Engine: {voice_status['engine']} | Model: {voice_status['model']}")
    assert "Piper TTS" in voice_status['engine']
    assert "en_US-amy-medium" in voice_status['model']

    # 7. Test Mute Toggle
    mute_state_1 = bridge.toggle_mute()
    print(f"[TEST 7] Toggle Mute: is_muted = {mute_state_1['is_muted']}")
    assert "is_muted" in mute_state_1

    mute_state_2 = bridge.toggle_mute()
    print(f"[TEST 8] Untoggle Mute: is_muted = {mute_state_2['is_muted']}")
    assert mute_state_1['is_muted'] != mute_state_2['is_muted']

    # 8. Test STT Engine Integration (Milestone 2B)
    stt_status = bridge.get_stt_status()
    print(f"[TEST 9] STT Engine: {stt_status['engine']} | Model: {stt_status['model']} | Mic: {stt_status['mic_available']}")
    assert "Faster-Whisper" in stt_status['engine']
    assert "tiny.en" in stt_status['model']

    # 9. Test Milestone 3: Personal Memory (Feature 2)
    print("\n--- Milestone 3: Memory Tests ---")
    mem_res = bridge.add_memory("The secret lab access code is delta-nine", category="protocols")
    assert mem_res["success"] is True
    mem_id = mem_res["id"]

    all_mems = bridge.get_memories("delta-nine")
    print(f"[TEST 10] Stored & retrieved memory: '{all_mems[0]['content']}' (ID: {mem_id})")
    assert len(all_mems) > 0
    assert "delta-nine" in all_mems[0]["content"]

    # Test sensitive data rejection
    sens_res = bridge.add_memory("My password is AdminPassword123")
    print(f"[TEST 11] Sensitive data filter check: success={sens_res['success']}")
    assert sens_res["success"] is False
    assert "Security Protocol Alert" in sens_res["error"]

    # Test update and delete memory
    upd_res = bridge.update_memory(mem_id, "The secret lab access code is omega-seven")
    assert upd_res["success"] is True
    del_res = bridge.delete_memory(mem_id)
    assert del_res["success"] is True
    print(f"[TEST 12] Memory update and deletion verified.")

    # 10. Test Milestone 3: Task Management (Feature 3)
    print("\n--- Milestone 3: Task Management Tests ---")
    task_res = bridge.add_task("Deploy defense satellite perimeter", due_date="tomorrow")
    assert task_res["success"] is True
    t_id = task_res["id"]
    print(f"[TEST 13] Created Task: #{t_id} '{task_res['title']}'")

    pending_tasks = bridge.get_tasks(completed=False)
    assert any(t["id"] == t_id for t in pending_tasks)

    # Mark completed
    toggle_res = bridge.toggle_task(t_id, completed=True)
    assert toggle_res["success"] is True
    completed_tasks = bridge.get_tasks(completed=True)
    assert any(t["id"] == t_id for t in completed_tasks)
    print(f"[TEST 14] Task completion toggled and verified.")

    # Delete task
    del_t_res = bridge.delete_task(t_id)
    assert del_t_res["success"] is True
    print(f"[TEST 15] Task deletion verified.")

    # 11. Test Milestone 3: Reminders (Feature 4)
    print("\n--- Milestone 3: Reminders Tests ---")
    now_past = (datetime.datetime.now() - datetime.timedelta(seconds=5)).isoformat()
    rem_res = bridge.add_reminder("Calibrate repulsor emitters", now_past)
    assert rem_res["success"] is True
    r_id = rem_res["id"]
    print(f"[TEST 16] Scheduled Reminder: #{r_id} '{rem_res['title']}'")

    due_list = bridge.check_due_reminders()
    print(f"[TEST 17] Due reminders checked: {len(due_list)} items triggered.")
    assert any(r["id"] == r_id for r in due_list)

    # Check that second check returns 0 duplicates
    due_list_2 = bridge.check_due_reminders()
    assert not any(r["id"] == r_id for r in due_list_2)
    print(f"[TEST 18] Duplicate notification prevention verified.")

    bridge.delete_reminder(r_id)

    # 12. Test Natural Language Memory & Task Commands via send_message
    print("\n--- Milestone 3: Dialogue Command Intent Tests ---")
    msg1 = bridge.send_message("Remember that my primary workstation is Jarvis Prime")
    print(f"[TEST 19] Natural Language Memory Store: {msg1['reply']}")
    assert "archived" in msg1["reply"].lower()

    msg2 = bridge.send_message("What do you remember about Jarvis Prime?")
    print(f"[TEST 20] Natural Language Memory Recall: {msg2['reply']}")
    assert "Jarvis Prime" in msg2["reply"]

    msg3 = bridge.send_message("Add a task to inspect arc reactor telemetry")
    print(f"[TEST 21] Natural Language Task Add: {msg3['reply']}")
    assert "registered" in msg3["reply"].lower()

    msg4 = bridge.send_message("What are my pending tasks?")
    print(f"[TEST 22] Natural Language Task List: {msg4['reply']}")
    assert "arc reactor" in msg4["reply"].lower()

    msg5 = bridge.send_message("Mark arc reactor telemetry task as complete")
    print(f"[TEST 23] Natural Language Task Complete: {msg5['reply']}")
    assert "complete" in msg5["reply"].lower()

    # Clean up test database entries
    bridge.db.delete_memory_by_content("Jarvis Prime")
    bridge.db.delete_task_by_title("arc reactor telemetry")

    # 13. Milestone 4.1: Safe Application Launcher Tests
    print("\n--- Milestone 4.1: Safe Application Launcher Tests ---")
    from unittest.mock import MagicMock, patch

    mock_proc = MagicMock()
    mock_proc.pid = 9999

    with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
        # A. Approved Apps Verification via Bridge
        approved = bridge.get_approved_apps()
        print(f"[TEST 24] Approved Applications List: {[a['name'] for a in approved]}")
        assert len(approved) == 5
        app_names = {a["name"] for a in approved}
        assert "Notepad" in app_names
        assert "Calculator" in app_names
        assert "File Explorer" in app_names
        assert "Paint" in app_names
        assert "Task Manager" in app_names

        # B. Launch Each Approved Application via send_message
        approved_test_cases = [
            ("Open Notepad", "Notepad"),
            ("Launch Calculator", "Calculator"),
            ("Open File Explorer", "File Explorer"),
            ("Start Paint", "Paint"),
            ("Open Task Manager", "Task Manager")
        ]
        for cmd, expected_name in approved_test_cases:
            mock_popen.reset_mock()
            res = bridge.send_message(cmd)
            print(f"[TEST 25] Command: '{cmd}' -> EDITH: {res['reply']}")
            assert expected_name in res["reply"]
            assert mock_popen.called
            # Verify security properties: shell=False, single binary argument list
            call_args, call_kwargs = mock_popen.call_args
            assert call_kwargs.get("shell") is False
            assert len(call_args[0]) == 1  # exactly [exe_path], never extra arguments or user text

        # C. Natural Language Command Variations
        nl_variations = [
            ("EDITH, please open notepad", "Notepad"),
            ("can you launch the calculator?", "Calculator"),
            ("start my paint app", "Paint"),
            ("run task manager", "Task Manager"),
            ("open files", "File Explorer")
        ]
        for cmd, expected_name in nl_variations:
            mock_popen.reset_mock()
            res = bridge.send_message(cmd)
            print(f"[TEST 26] NL Variation: '{cmd}' -> EDITH: {res['reply']}")
            assert expected_name in res["reply"]
            assert mock_popen.called
            _, call_kwargs = mock_popen.call_args
            assert call_kwargs.get("shell") is False

        # D. Rejection of Unapproved / Unknown Applications
        unapproved_commands = [
            "open cmd",
            "launch powershell",
            "start cmd.exe",
            "run powershell.exe",
            "open chrome",
            "launch firefox",
            "start virus.exe",
            "open spotify"
        ]
        for cmd in unapproved_commands:
            mock_popen.reset_mock()
            res = bridge.send_message(cmd)
            print(f"[TEST 27] Unapproved Command: '{cmd}' -> EDITH: {res['reply'][:65]}...")
            assert "Security Protocol Notice" in res["reply"] or "not on the approved application allowlist" in res["reply"]
            assert not mock_popen.called  # MUST NEVER launch unapproved applications!

        # E. Rejection of Shell Injection / Malicious Command Chaining
        injection_attempts = [
            "launch calc && whoami",
            "open notepad; rm -rf /",
            "start paint | format c:",
            "run `calc`",
            "open calc > output.txt",
            "launch notepad --arg evil",
            "open notepad & calc",
            "start calc\nwhoami"
        ]
        for cmd in injection_attempts:
            mock_popen.reset_mock()
            res = bridge.send_message(cmd)
            print(f"[TEST 28] Injection Attempt: '{cmd}' -> EDITH: {res['reply'][:65]}...")
            assert not mock_popen.called  # MUST NEVER execute injection payloads!

        # F. Direct Bridge Method launch_app
        mock_popen.reset_mock()
        direct_ok = bridge.launch_app("notepad")
        print(f"[TEST 29] Direct bridge launch_app('notepad'): success={direct_ok['success']}")
        assert direct_ok["success"] is True
        assert direct_ok["app_id"] == "notepad"
        assert mock_popen.called

        mock_popen.reset_mock()
        direct_blocked = bridge.launch_app("powershell")
        print(f"[TEST 30] Direct bridge launch_app('powershell'): success={direct_blocked['success']}")
        assert direct_blocked["success"] is False
        assert "not in the approved" in direct_blocked["error"]
        assert not mock_popen.called

        # G. Non-App "Open" Directives Disambiguation
        non_app_queries = [
            "show memories",
            "open memories"
        ]
        for query in non_app_queries:
            mock_popen.reset_mock()
            res = bridge.send_message(query)
            print(f"[TEST 31] Non-app intent disambiguation: '{query}' -> EDITH: {res['reply'][:60]}...")
            assert not mock_popen.called
            assert "Security Protocol Notice" not in res["reply"]

    # 14. Milestone 4.2: Safe Website Launcher Tests
    print("\n--- Milestone 4.2: Safe Website Launcher Tests ---")
    import webbrowser
    with patch("webbrowser.open_new_tab", return_value=True) as mock_web_tab, \
         patch("webbrowser.open", return_value=True) as mock_web_open, \
         patch("subprocess.Popen", return_value=mock_proc) as mock_popen:

        # A. Approved Websites List via Bridge
        approved_sites = bridge.get_approved_websites()
        print(f"[TEST 32] Approved Websites List: {[w['name'] for w in approved_sites]}")
        assert len(approved_sites) == 8
        site_names = {w["name"] for w in approved_sites}
        for expected in ("Google", "YouTube", "ChatGPT", "Wikipedia", "Gmail", "GitHub", "Reddit", "Stack Overflow"):
            assert expected in site_names

        # B. Launch Each Approved Website via send_message
        approved_web_cases = [
            ("Open YouTube", "YouTube", "https://www.youtube.com/"),
            ("Launch Google", "Google", "https://www.google.com/"),
            ("Go to ChatGPT", "ChatGPT", "https://chatgpt.com/"),
            ("Open Gmail", "Gmail", "https://mail.google.com/"),
            ("Take me to GitHub", "GitHub", "https://github.com/"),
            ("Visit Wikipedia", "Wikipedia", "https://www.wikipedia.org/"),
            ("Open Reddit", "Reddit", "https://www.reddit.com/"),
            ("Go to Stack Overflow", "Stack Overflow", "https://stackoverflow.com/")
        ]
        for cmd, expected_name, expected_url in approved_web_cases:
            mock_web_tab.reset_mock()
            mock_popen.reset_mock()
            res = bridge.send_message(cmd)
            print(f"[TEST 33] Command: '{cmd}' -> EDITH: {res['reply']}")
            assert expected_name in res["reply"]
            assert mock_web_tab.called
            # Ensure the exact pre-approved HTTPS URL was passed
            call_url = mock_web_tab.call_args[0][0]
            assert call_url == expected_url
            assert not mock_popen.called  # Websites must NEVER trigger subprocess.Popen

        # C. Natural Language Phrase Variations & Aliases
        nl_web_variations = [
            ("EDITH, please open youtube", "YouTube", "https://www.youtube.com/"),
            ("can you launch the google search?", "Google", "https://www.google.com/"),
            ("take me to git hub", "GitHub", "https://github.com/"),
            ("visit wiki", "Wikipedia", "https://www.wikipedia.org/"),
            ("go to chat gpt", "ChatGPT", "https://chatgpt.com/"),
            ("open my email", "Gmail", "https://mail.google.com/"),
            ("browse to reddit.com", "Reddit", "https://www.reddit.com/"),
            ("navigate to stackoverflow", "Stack Overflow", "https://stackoverflow.com/")
        ]
        for cmd, expected_name, expected_url in nl_web_variations:
            mock_web_tab.reset_mock()
            mock_popen.reset_mock()
            res = bridge.send_message(cmd)
            print(f"[TEST 34] NL Web Variation: '{cmd}' -> EDITH: {res['reply']}")
            assert expected_name in res["reply"]
            assert mock_web_tab.called
            assert mock_web_tab.call_args[0][0] == expected_url

        # D. Rejection of Unknown Websites
        unapproved_web_commands = [
            "open facebook",
            "go to twitter",
            "visit netflix",
            "take me to amazon",
            "browse to instagram",
            "open tiktok",
            "visit twitch",
            "go to linkedin"
        ]
        for cmd in unapproved_web_commands:
            mock_web_tab.reset_mock()
            mock_popen.reset_mock()
            res = bridge.send_message(cmd)
            print(f"[TEST 35] Unapproved Web Command: '{cmd}' -> EDITH: {res['reply'][:65]}...")
            assert "Security Protocol Notice" in res["reply"]
            assert "approved website allowlist" in res["reply"]
            assert not mock_web_tab.called  # MUST NEVER launch browser for unapproved sites
            assert not mock_popen.called

        # E. Rejection of Arbitrary URLs, IP addresses, and HTTP links
        arbitrary_url_commands = [
            "open https://malicious.site",
            "go to http://192.168.1.1",
            "visit bit.ly/xyz",
            "browse to evil-domain.com",
            "take me to http://insecure-site.com",
            "open 10.0.0.1"
        ]
        for cmd in arbitrary_url_commands:
            mock_web_tab.reset_mock()
            mock_popen.reset_mock()
            res = bridge.send_message(cmd)
            print(f"[TEST 36] Arbitrary URL: '{cmd}' -> EDITH: {res['reply'][:65]}...")
            assert "Security Protocol Notice" in res["reply"]
            assert not mock_web_tab.called
            assert not mock_popen.called

        # F. Rejection of Shell Injection / Malicious Chaining
        web_injections = [
            "go to youtube && whoami",
            "visit google; rm -rf /",
            "open chatgpt | format c:",
            "take me to `calc`",
            "navigate to youtube > log.txt"
        ]
        for cmd in web_injections:
            mock_web_tab.reset_mock()
            mock_popen.reset_mock()
            res = bridge.send_message(cmd)
            print(f"[TEST 37] Web Injection: '{cmd}' -> EDITH: {res['reply'][:65]}...")
            assert not mock_web_tab.called
            assert not mock_popen.called

        # G. Direct Bridge Method launch_website
        mock_web_tab.reset_mock()
        direct_web_ok = bridge.launch_website("youtube")
        print(f"[TEST 38] Direct bridge launch_website('youtube'): success={direct_web_ok['success']}")
        assert direct_web_ok["success"] is True
        assert direct_web_ok["url"] == "https://www.youtube.com/"
        assert mock_web_tab.called

        mock_web_tab.reset_mock()
        direct_web_blocked = bridge.launch_website("facebook")
        print(f"[TEST 39] Direct bridge launch_website('facebook'): success={direct_web_blocked['success']}")
        assert direct_web_blocked["success"] is False
        assert "not in the approved website allowlist" in direct_web_blocked["error"]
        assert not mock_web_tab.called

        # H. Coexistence: Application Launcher Commands vs Website Commands
        print("\n--- Coexistence Tests: App Launcher vs Web Launcher ---")
        coexistence_tests = [
            ("Open Calculator", "app", "Calculator"),
            ("Open YouTube", "web", "YouTube"),
            ("Open Notepad", "app", "Notepad"),
            ("Launch Google", "web", "Google"),
            ("Start Paint", "app", "Paint"),
            ("Go to ChatGPT", "web", "ChatGPT"),
            ("Open File Explorer", "app", "File Explorer"),
            ("Take me to GitHub", "web", "GitHub"),
            ("Open Task Manager", "app", "Task Manager"),
            ("Visit Wikipedia", "web", "Wikipedia")
        ]
        for cmd, expected_type, expected_name in coexistence_tests:
            mock_popen.reset_mock()
            mock_web_tab.reset_mock()
            res = bridge.send_message(cmd)
            print(f"[TEST 40] Coexistence: '{cmd}' [{expected_type.upper()}] -> EDITH: {res['reply']}")
            assert expected_name in res["reply"]
            if expected_type == "app":
                assert mock_popen.called, f"Expected app launch for '{cmd}'"
                assert not mock_web_tab.called, f"Browser should not be called for app '{cmd}'"
            else:
                assert mock_web_tab.called, f"Expected web launch for '{cmd}'"
                assert not mock_popen.called, f"Popen should not be called for web '{cmd}'"

    # 15. Milestone 4.3: Safe Local File Search Tests
    print("\n--- Milestone 4.3: Safe Local File Search Tests ---")
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as temp_root, \
         patch("os.startfile") as mock_startfile:

        temp_p = Path(temp_root).resolve()
        docs_dir = temp_p / "Documents"
        down_dir = temp_p / "Downloads"
        desk_dir = temp_p / "Desktop"
        docs_dir.mkdir()
        down_dir.mkdir()
        desk_dir.mkdir()

        # Populate test fixtures
        (docs_dir / "resume_2026.pdf").write_text("Mock resume", encoding="utf-8")
        (docs_dir / "project_report.docx").write_text("Mock report", encoding="utf-8")
        (docs_dir / "budget_planning.xlsx").write_text("Mock budget", encoding="utf-8")
        (docs_dir / "notes.txt").write_text("Mock notes", encoding="utf-8")
        (docs_dir / "Projects").mkdir()
        (docs_dir / "Projects" / "alpha_doc.txt").write_text("Alpha", encoding="utf-8")

        # Hidden folder (should be excluded)
        hidden_dir = docs_dir / ".hidden_folder"
        hidden_dir.mkdir()
        (hidden_dir / "secret_document.pdf").write_text("Hidden", encoding="utf-8")

        # Downloads items
        (down_dir / "landscape_photo.png").write_text("Mock PNG", encoding="utf-8")
        (down_dir / "diagram.jpg").write_text("Mock JPG", encoding="utf-8")
        (down_dir / "analysis_script.py").write_text("print('hello')", encoding="utf-8")
        (down_dir / "installer.exe").write_bytes(b"MZ\x00\x00")
        (down_dir / "danger.bat").write_text("@echo off", encoding="utf-8")

        # Desktop items
        (desk_dir / "budget_q4.csv").write_text("1,2,3", encoding="utf-8")
        (desk_dir / "main_script.py").write_text("print('main')", encoding="utf-8")

        # Configure bridge file_search with test sandbox roots + a missing root
        missing_dir = temp_p / "MissingFolder"
        test_roots = {
            "documents": docs_dir,
            "downloads": down_dir,
            "desktop": desk_dir,
            "missing": missing_dir
        }
        from core.file_search import FileSearchEngine
        test_engine = FileSearchEngine(db=bridge.db, custom_roots=test_roots)
        bridge.file_search = test_engine
        bridge.brain.file_search = test_engine

        # A. Filename Partial Matching
        res41 = bridge.send_message("Search for resume")
        print(f"[TEST 41] Search 'resume':\n{res41['reply']}")
        assert "resume_2026.pdf" in res41["reply"]
        assert not mock_startfile.called  # Search must NOT open files automatically!

        # B. Extension Filtering ("Find my PDF files")
        res42 = bridge.send_message("Find my PDF files")
        print(f"[TEST 42] Search 'PDF files':\n{res42['reply']}")
        assert "resume_2026.pdf" in res42["reply"]
        assert "secret_document.pdf" not in res42["reply"]  # Hidden folder excluded!

        # C. Folder-Name Searching ("Find folders named Projects")
        res43 = bridge.send_message("Find folders named Projects")
        print(f"[TEST 43] Search folders 'Projects':\n{res43['reply']}")
        assert "Projects" in res43["reply"]
        assert "Folder" in res43["reply"]

        # D. Scope-Restricted Search ("Find images in Downloads")
        res44 = bridge.send_message("Find images in Downloads")
        print(f"[TEST 44] Search 'images in Downloads':\n{res44['reply']}")
        assert "landscape_photo.png" in res44["reply"]
        assert "diagram.jpg" in res44["reply"]
        assert "analysis_script.py" not in res44["reply"]

        # E. Type Filtering ("Find Python files")
        res45 = bridge.send_message("Find Python files")
        print(f"[TEST 45] Search 'Python files':\n{res45['reply']}")
        assert "analysis_script.py" in res45["reply"]
        assert "main_script.py" in res45["reply"]

        # F. Multiple Keyword Matching ("Search for files named budget")
        res46 = bridge.send_message("Search for files named budget")
        print(f"[TEST 46] Search 'budget':\n{res46['reply']}")
        assert "budget_planning.xlsx" in res46["reply"]
        assert "budget_q4.csv" in res46["reply"]

        # G. Missing / Inaccessible Directory Handling
        # Search scope="missing" gracefully handles non-existent directory without crashing
        res47 = bridge.send_message("Find files in missing")
        print(f"[TEST 47] Missing directory search: {res47['reply'][:60]}...")
        assert "No matching files" in res47["reply"] or "registers report zero" in res47["reply"]

        # H. Pagination (Over 10 Results)
        # Create 14 additional dummy files in docs_dir
        for i in range(1, 15):
            (docs_dir / f"audit_log_{i:02d}.txt").write_text(f"Log {i}", encoding="utf-8")

        res48 = bridge.send_message("Search for audit_log")
        print(f"[TEST 48] Search pagination page 1: Showing {test_engine.current_page}")
        assert "Showing 1-10 of 14" in res48["reply"]
        assert "audit_log_01.txt" in res48["reply"]

        res48_p2 = bridge.send_message("Show more results")
        print(f"[TEST 48] Search pagination page 2: Showing {test_engine.current_page}")
        assert "Showing 11-14 of 14" in res48_p2["reply"]
        assert "audit_log_14.txt" in res48_p2["reply"]

        # I. Safe File Opening on Explicit User Action
        bridge.send_message("Search for resume")
        assert not mock_startfile.called  # Must not open automatically!

        open_res = bridge.send_message("Open result 1")
        print(f"[TEST 49] Open file 1: {open_res['reply']}")
        assert "Opening 'resume_2026.pdf'" in open_res["reply"]
        assert mock_startfile.called
        assert "resume_2026.pdf" in str(mock_startfile.call_args[0][0])

        # J. Safe Folder Opening on Explicit User Action
        mock_startfile.reset_mock()
        open_folder_res = bridge.send_message("Open folder 1")
        print(f"[TEST 50] Open folder 1: {open_folder_res['reply']}")
        assert "Opening folder for 'resume_2026.pdf'" in open_folder_res["reply"]
        assert mock_startfile.called

        # K. Binary Executable Execution Protection
        bridge.send_message("Search for installer")
        mock_startfile.reset_mock()
        exec_blocked = bridge.send_message("Open result 1")
        print(f"[TEST 51] Blocked executable: {exec_blocked['reply']}")
        assert "Security Protocol Notice" in exec_blocked["reply"]
        assert "blocked" in exec_blocked["reply"]
        assert not mock_startfile.called  # MUST NEVER execute .exe!

        # L. Path Traversal & Escaping Approved Roots Protection
        traversal_ok, traversal_msg = test_engine.open_result(999)  # Invalid index
        assert traversal_ok is False
        assert "Invalid result index" in traversal_msg

        # Manually inject an escaping item into last_results
        test_engine.last_results = [{
            "name": "system_file.dll",
            "path": r"C:\Windows\System32\cmd.exe",
            "is_dir": False,
            "type_desc": "Binary",
            "folder_location": r"C:\Windows\System32"
        }]
        mock_startfile.reset_mock()
        escape_ok, escape_msg = test_engine.open_result(1)
        print(f"[TEST 52] Root escape prevention: {escape_msg}")
        assert escape_ok is False
        assert "Security Protocol Notice" in escape_msg or "outside authorized roots" in escape_msg
        assert not mock_startfile.called

        # M. Searching EDITH Project Folder explicitly
        res_edith = bridge.send_message("Find test files in EDITH")
        print(f"[TEST 53] Search EDITH project folder: {res_edith['reply'][:70]}...")
        assert "test_backend.py" in res_edith["reply"] or "test" in res_edith["reply"].lower()

    print("\n" + "=" * 70)
    print(">>> ALL MILESTONE 1, 2A, 2B, 3, 4.1, 4.2 & 4.3 BACKEND & BRIDGE TESTS PASSED! <<<")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()



