"""
Safe Windows Application Launcher for E.D.I.T.H. (Milestone 4.1)
Enforces a strict, hardcoded allowlist of approved Windows desktop applications.
Never executes arbitrary commands, never passes user input to a shell,
and guarantees shell=False on all process spawning.
"""
import os
import re
import shutil
import logging
import subprocess
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("EDITH.AppLauncher")

# ==============================================================================
# STRICT APPLICATION ALLOWLIST (Milestone 4.1 Approved Applications)
# ==============================================================================
APPROVED_APPS: Dict[str, Dict[str, Any]] = {
    "notepad": {
        "display_name": "Notepad",
        "description": "Windows Text Editor",
        "aliases": [
            "notepad",
            "note pad",
            "text editor",
            "notes editor"
        ],
        "executables": [
            "notepad.exe",
            "notepad",
            r"C:\Windows\System32\notepad.exe",
            r"C:\Windows\notepad.exe"
        ]
    },
    "calculator": {
        "display_name": "Calculator",
        "description": "Windows Calculator",
        "aliases": [
            "calculator",
            "calc"
        ],
        "executables": [
            "calc.exe",
            "calc",
            r"C:\Windows\System32\calc.exe"
        ]
    },
    "explorer": {
        "display_name": "File Explorer",
        "description": "Windows File Explorer",
        "aliases": [
            "file explorer",
            "explorer",
            "files",
            "file manager",
            "my computer",
            "windows explorer"
        ],
        "executables": [
            "explorer.exe",
            "explorer",
            r"C:\Windows\explorer.exe"
        ]
    },
    "paint": {
        "display_name": "Paint",
        "description": "Microsoft Paint",
        "aliases": [
            "paint",
            "mspaint",
            "ms paint"
        ],
        "executables": [
            "mspaint.exe",
            "mspaint",
            r"C:\Windows\System32\mspaint.exe"
        ]
    },
    "task_manager": {
        "display_name": "Task Manager",
        "description": "Windows Task Manager",
        "aliases": [
            "task manager",
            "taskmanager",
            "taskmgr",
            "task monitor",
            "system monitor",
            "task management"
        ],
        "executables": [
            "taskmgr.exe",
            "taskmgr",
            r"C:\Windows\System32\taskmgr.exe"
        ]
    }
}

class AppLauncher:
    """
    Safe Application Launcher that strictly restricts desktop execution
    to verified Windows system utilities from an explicit allowlist.
    """

    def __init__(self, db: Optional[Any] = None):
        self.db = db
        self.approved_apps = APPROVED_APPS

    def get_approved_apps(self) -> List[Dict[str, str]]:
        """Return the list of approved applications for UI and guidance."""
        return [
            {
                "id": app_id,
                "name": data["display_name"],
                "description": data["description"]
            }
            for app_id, data in self.approved_apps.items()
        ]

    def match_app(self, raw_name: str) -> Optional[str]:
        """
        Match a raw user phrase against the approved applications allowlist.
        Strips common filler articles ('the', 'my', 'a', 'app', 'application').
        Strictly rejects shell metacharacters and requires an exact alias match.
        Returns the matching app_id or None if unapproved.
        """
        clean = raw_name.strip().lower()
        # Strip common trailing punctuation
        clean = clean.rstrip(".!?,")

        # Reject any shell metacharacters, arguments, or chaining operators
        if any(char in clean for char in (";", "&", "|", ">", "<", "`", "$", "\n", "\\", "/", "-")):
            return None

        # Strip filler words
        clean = re.sub(r"^(?:the|my|a|an)\s+", "", clean).strip()
        clean = re.sub(r"\s+(?:app|application|program|tool)$", "", clean).strip()

        # Exact alias match only
        for app_id, data in self.approved_apps.items():
            if clean in data["aliases"] or clean == app_id:
                return app_id

        return None

    def resolve_executable(self, app_id: str) -> Optional[str]:
        """
        Resolve the safe, verified filesystem path for an approved application.
        Strictly restricts candidate paths to the hardcoded allowlist.
        """
        if app_id not in self.approved_apps:
            return None

        candidates = self.approved_apps[app_id]["executables"]

        # Check candidate executables via PATH or absolute paths
        for cand in candidates:
            # If candidate is an absolute path that exists
            if os.path.isabs(cand) and os.path.isfile(cand):
                return cand

            # Search in system PATH
            found = shutil.which(cand)
            if found and os.path.isfile(found):
                return found

        return None

    def launch_app(self, app_id: str) -> Dict[str, Any]:
        """
        Launch an approved application safely using subprocess.Popen.
        Guarantees:
        - shell=False is strictly enforced.
        - No user input is ever passed to the operating system shell or command line.
        - Detached execution prevents blocking EDITH's thread or loop.
        """
        if app_id not in self.approved_apps:
            return {
                "success": False,
                "error": f"Security Notice: '{app_id}' is not in the approved application allowlist."
            }

        app_info = self.approved_apps[app_id]
        display_name = app_info["display_name"]
        exe_path = self.resolve_executable(app_id)

        if not exe_path:
            msg = f"Application '{display_name}' could not be located on this Windows installation."
            logger.warning(msg)
            return {"success": False, "error": msg}

        try:
            # Determine process creation flags on Windows to detach cleanly
            creation_flags = 0
            if hasattr(subprocess, "DETACHED_PROCESS"):
                creation_flags = subprocess.DETACHED_PROCESS

            # Strictly safe: shell=False, no user parameters, exact binary path
            proc = subprocess.Popen(
                [exe_path],
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creation_flags
            )

            # Audit log into SQLite database if connected
            if self.db:
                self.db.log_audit("INFO", "APP_LAUNCH", f"Launched approved app '{display_name}' (PID: {proc.pid})")

            logger.info(f"Successfully launched approved application: {display_name} (PID: {proc.pid})")
            return {
                "success": True,
                "app_id": app_id,
                "display_name": display_name,
                "pid": proc.pid,
                "path": exe_path
            }

        except Exception as e:
            err_msg = f"Failed to launch {display_name}: {e}"
            logger.error(err_msg)
            if self.db:
                self.db.log_audit("ERROR", "APP_LAUNCH_FAIL", err_msg)
            return {"success": False, "error": err_msg}

    def handle_command(self, user_input: str, callsign: str = "Boss") -> Tuple[bool, str]:
        """
        Parse and process natural-language launch commands.
        Returns:
            (is_launch_command: bool, reply_message: str)
        If the command is not an application launch attempt, returns (False, "").
        If it is a launch attempt:
            - Approved: executes safe launch and returns in-character confirmation.
            - Unapproved or Malicious: safely rejects and returns protocol explanation.
        """
        clean = user_input.strip()
        lower = clean.lower()

        # Check if the user input is an app launch directive:
        # e.g., "open notepad", "launch calculator", "start paint", "run task manager"
        # Support polite prefixes: "edith, please open notepad", "can you launch paint?"
        launch_regex = r"^(?:edith[,\s]+)?(?:please\s+)?(?:can\s+you\s+)?(?:open|launch|start|run)\b(?:\s+(.+))?$"
        match = re.match(launch_regex, lower)

        if not match:
            return False, ""

        raw_target = match.group(1)

        # Case 1: User just said "open", "launch", "start", "run" without naming an app
        if not raw_target or not raw_target.strip():
            approved_list = ", ".join(d["display_name"] for d in self.approved_apps.values())
            return True, (
                f"Please specify which approved application you would like me to open, {callsign}. "
                f"Currently authorized: {approved_list}."
            )

        target_cleaned = raw_target.strip().rstrip(".!?,")

        # Exclude non-app intents that use "open" or "start" (e.g., "open memories", "open settings", "open result 1")
        if target_cleaned in ("memories", "memory", "my memories", "notes", "my notes", "tasks", "my tasks", "reminders", "settings"):
            return False, ""
        if re.match(r"^(?:result|file|folder|item)\s+\d+\b", target_cleaned):
            return False, ""

        # Match against the strict allowlist
        matched_id = self.match_app(target_cleaned)

        if not matched_id:
            # If target is handled by web launcher (e.g., "open youtube", "open google"), hand off cleanly
            try:
                from core.web_launcher import WebLauncher
                web_l = WebLauncher()
                if web_l.match_website(target_cleaned) or web_l.is_web_target(target_cleaned):
                    return False, ""
            except Exception:
                pass

            # Unapproved or unknown application: REJECT SAFELY
            approved_list = ", ".join(d["display_name"] for d in self.approved_apps.values())
            return True, (
                f"Security Protocol Notice: '{target_cleaned}' is not on the approved application allowlist, {callsign}. "
                f"For system safety, I can currently only launch: {approved_list}."
            )

        # Approved application: Launch safely
        result = self.launch_app(matched_id)

        if result["success"]:
            display_name = result["display_name"]
            confirmations = [
                f"Opening {display_name}, {callsign}. Process initialized.",
                f"Launching {display_name} now, {callsign}.",
                f"Accessing {display_name}. Subsystem running, {callsign}."
            ]
            import random
            return True, random.choice(confirmations)
        else:
            return True, f"Notice: Could not launch {result.get('display_name', target_cleaned)}, {callsign}. {result.get('error', '')}"
