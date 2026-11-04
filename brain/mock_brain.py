"""
E.D.I.T.H. Mock Brain Module (Milestone 3)
Delivers intelligent, contextual, and cinematic EDITH responses
with zero external dependencies or heavy AI model overhead.
Fully integrated with persistent local SQLite memory, tasks, and reminders.
"""
import re
import datetime
import random
from typing import Dict, Any, Optional, Tuple
from .base import BaseBrain

def check_sensitive_content(text: str) -> Optional[str]:
    """
    Check if the text contains sensitive credentials, passwords, financial
    information, or private cryptographic keys that must NOT be stored.
    """
    lower = text.lower()

    # Passwords & logins
    if re.search(r"\b(password|passcode|secret\s+code|login\s+pin)\b", lower):
        return "passwords or login credentials"

    # Financial details
    if re.search(r"\b(credit\s*card|debit\s*card|cvv|cvc|bank\s*account|routing\s*number)\b", lower):
        return "financial credentials or payment details"
    if re.search(r"\b(?:\d[ -]*?){13,16}\b", text):
        digits = re.sub(r"\D", "", text)
        if len(digits) in (15, 16):
            return "credit card numbers"

    # Private keys, API tokens
    if re.search(r"(-----BEGIN\s+[A-Z\s]+PRIVATE\s+KEY|ssh-rsa|ecdsa-sha2|ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,})", text):
        return "private cryptographic keys or API tokens"
    if re.search(r"\b(api[_\s]?key|secret[_\s]?key|private[_\s]?key)\b", lower):
        return "API or private keys"

    return None

def parse_time_expression(expr: str) -> Tuple[Optional[datetime.datetime], str]:
    """
    Parse a human-readable time expression into a target datetime.
    Supports relative (e.g., 'in 10 minutes', 'in 2 hours') and
    clock times (e.g., 'at 3:30 pm', 'at 15:00').
    Returns (datetime_obj, friendly_string).
    """
    now = datetime.datetime.now()
    expr = expr.strip()

    # 1. Relative: 'in X minutes/hours/seconds'
    rel_match = re.search(r"\bin\s+(\d+)\s*(minute|min|hour|hr|second|sec)s?\b", expr, re.IGNORECASE)
    if rel_match:
        qty = int(rel_match.group(1))
        unit = rel_match.group(2).lower()
        if unit.startswith("min"):
            target = now + datetime.timedelta(minutes=qty)
            friendly = f"{qty} minute{'s' if qty != 1 else ''} ({target.strftime('%I:%M %p')})"
        elif unit.startswith("hour") or unit.startswith("hr"):
            target = now + datetime.timedelta(hours=qty)
            friendly = f"{qty} hour{'s' if qty != 1 else ''} ({target.strftime('%I:%M %p')})"
        else:
            target = now + datetime.timedelta(seconds=qty)
            friendly = f"{qty} seconds ({target.strftime('%I:%M:%S %p')})"
        return target, friendly

    # 2. Clock time: 'at HH:MM [am/pm]' or 'at HH [am/pm]'
    clock_match = re.search(r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", expr, re.IGNORECASE)
    if clock_match:
        hour = int(clock_match.group(1))
        minute = int(clock_match.group(2) or 0)
        meridiem = clock_match.group(3)

        if meridiem:
            meridiem = meridiem.lower()
            if meridiem == "pm" and hour < 12:
                hour += 12
            elif meridiem == "am" and hour == 12:
                hour = 0

        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        # If time already passed today, advance to tomorrow
        if target <= now:
            target += datetime.timedelta(days=1)
            day_str = "tomorrow"
        else:
            day_str = "today"
        friendly = f"{day_str} at {target.strftime('%I:%M %p')}"
        return target, friendly

    return None, ""

class MockBrain(BaseBrain):
    """
    Intelligent rule & heuristic brain implementing the calm,
    competent, cinematic EDITH persona for Milestone 4.1.
    """

    def __init__(self, db: Optional[Any] = None, launcher: Optional[Any] = None, web_launcher: Optional[Any] = None, file_search: Optional[Any] = None):
        self.callsign = "Boss"
        self.db = db
        self.launcher = launcher
        self.web_launcher = web_launcher
        self.file_search = file_search

    def get_name(self) -> str:
        return "EDITH Mock Core (Rule-Based v4.3)"

    def is_available(self) -> bool:
        return True

    def generate_response(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        clean = user_input.strip()
        lower = clean.lower()

        telemetry = context.get("telemetry", {}) if context else {}
        callsign = context.get("user_callsign", self.callsign) if context else self.callsign
        db = self.db or (context.get("db") if context else None)
        launcher = self.launcher or (context.get("launcher") if context else None)
        web_launcher = self.web_launcher or (context.get("web_launcher") if context else None)

        # ============================================================
        # 0A. APPLICATION LAUNCH DIRECTIVES (Milestone 4.1)
        # ============================================================
        if launcher is None:
            try:
                from core.app_launcher import AppLauncher
                launcher = AppLauncher(db=db)
                self.launcher = launcher
            except Exception:
                launcher = None

        if launcher:
            is_launch, launch_reply = launcher.handle_command(clean, callsign=callsign)
            if is_launch:
                return launch_reply

        # ============================================================
        # 0B. WEBSITE LAUNCH DIRECTIVES (Milestone 4.2)
        # ============================================================
        if web_launcher is None:
            try:
                from core.web_launcher import WebLauncher
                web_launcher = WebLauncher(db=db)
                self.web_launcher = web_launcher
            except Exception:
                web_launcher = None

        if web_launcher:
            is_web, web_reply = web_launcher.handle_command(clean, callsign=callsign)
            if is_web:
                return web_reply

        # ============================================================
        # 0C. LOCAL FILE SEARCH DIRECTIVES (Milestone 4.3)
        # ============================================================
        file_search = self.file_search or (context.get("file_search") if context else None)
        if file_search is None:
            try:
                from core.file_search import FileSearchEngine
                file_search = FileSearchEngine(db=db)
                self.file_search = file_search
            except Exception:
                file_search = None

        if file_search:
            is_search, search_reply = file_search.handle_command(clean, callsign=callsign)
            if is_search:
                return search_reply

        # ============================================================
        # 1. PERSONAL MEMORY & NOTES (Milestone 3, Feature 2)
        # ============================================================

        # 1A. Explicit Memory Storage: "Remember that...", "Remember: ...", "Take note..."
        rem_store_match = re.match(r"^(?:edith[,\s]+)?(?:remember\s+that|remember[:\s]+|take\s+(?:a\s+)?note[:\s]+|note\s+that|note[:\s]+)(.+)$", lower)
        if rem_store_match and not re.search(r"\b(what|do\s+you|how)\b", lower):
            raw_content = clean[rem_store_match.start(1):].strip()
            # Clean leading colons or quotes
            raw_content = raw_content.lstrip(": \t'\"").rstrip("'\"")

            # Privacy and sensitive information check
            sensitive_reason = check_sensitive_content(raw_content)
            if sensitive_reason:
                return (
                    f"Security Protocol Alert: I cannot store {sensitive_reason} in local memory for your protection, {callsign}. "
                    f"Credential logging is strictly blocked."
                )

            if db:
                db.add_memory(raw_content, category="user_note")
                return f"Memory archived, {callsign}: '{raw_content}'. Stored safely in local encrypted repository."
            return f"Memory noted, {callsign}: '{raw_content}'."

        # 1B. Memory Recall / Query: "What do you remember about [topic]?", "What do you know about [topic]?"
        rem_query_match = re.search(r"\b(?:what\s+(?:do\s+you\s+remember|do\s+you\s+know)\s+about|do\s+you\s+remember|search\s+memory\s+for)\s+(.+)", lower)
        if rem_query_match:
            query = rem_query_match.group(1).strip().rstrip("?").strip()
            # Strip common stop words for clean SQLite search
            cleaned_query = re.sub(r"^(?:my|the|a|an|our)\s+", "", query).strip()

            if db:
                memories = db.get_memories(search=cleaned_query)
                if memories:
                    lines = [f"- {m['content']} (Logged: {m['created_at'][:10]})" for m in memories[:5]]
                    return f"Here is what I have archived regarding '{query}', {callsign}:\n" + "\n".join(lines)
                else:
                    # NEVER pretend to remember information that is not stored
                    return f"I do not have any saved memories regarding '{query}', {callsign}. Local registers report zero matches."
            return f"Memory subsystem is not connected, {callsign}."

        # 1C. List / Show All Memories: "What do you remember?", "Show memories", "List memories"
        if re.search(r"\b(?:what\s+do\s+you\s+remember|show\s+(?:all\s+)?memories|list\s+(?:all\s+)?memories|show\s+(?:my\s+)?notes|list\s+(?:my\s+)?notes)\b", lower):
            if db:
                memories = db.get_memories(limit=15)
                if memories:
                    lines = [f"[{i+1}] {m['content']}" for i, m in enumerate(memories)]
                    return f"Active Memories Archived for {callsign} ({len(memories)} total):\n" + "\n".join(lines)
                else:
                    return f"Memory registers are currently empty, {callsign}. You have not asked me to archive any notes yet."
            return f"Memory archive empty, {callsign}."

        # 1D. Forget / Delete Memory: "Forget that particular note", "Forget that my project...", "Forget [X]"
        rem_forget_match = re.search(r"\b(?:forget\s+that|forget|delete\s+memory|erase\s+memory)\s+(.+)", lower)
        if rem_forget_match and not re.search(r"\b(task|reminder)\b", lower):
            query = rem_forget_match.group(1).strip().rstrip(".").strip()
            cleaned_query = re.sub(r"^(?:particular\s+note|that\s+note|my\s+note)\s*", "", query).strip()
            if not cleaned_query:
                cleaned_query = query

            if db:
                # If query contains digits, try deleting by ID
                if cleaned_query.isdigit():
                    success = db.delete_memory(int(cleaned_query))
                    if success:
                        return f"Memory entry #{cleaned_query} erased, {callsign}."
                deleted_count = db.delete_memory_by_content(cleaned_query)
                if deleted_count > 0:
                    return f"Memory purged, {callsign}. Erased {deleted_count} entry matching '{cleaned_query}' from local repository."
                else:
                    return f"No matching memory found for '{cleaned_query}', {callsign}. Registers remain unchanged."
            return f"Memory erased, {callsign}."

        # ============================================================
        # 2. TASK MANAGEMENT (Milestone 3, Feature 3)
        # ============================================================

        # 2A. Add Task: "Add a task to finish documentation", "Add a task to test EDITH", "Add task [X]"
        task_add_match = re.match(r"^(?:edith[,\s]+)?(?:add\s+(?:a\s+)?task\s+(?:to\s+)?|create\s+(?:a\s+)?task\s+(?:to\s+)?|new\s+task[:\s]+)(.+)$", lower)
        if task_add_match:
            task_title = clean[task_add_match.start(1):].strip().rstrip(".")
            # Check for optional due date expression
            due_date = None
            due_match = re.search(r"\b(due\s+(?:tomorrow|today|next\s+week|by\s+[A-Za-z]+|\d{1,2}/\d{1,2}))\b", task_title, re.IGNORECASE)
            if due_match:
                due_date = due_match.group(1)
                task_title = task_title[:due_match.start()].strip().rstrip("-:, ")

            if db:
                db.add_task(task_title, due_date=due_date)
                due_str = f" (Due: {due_date})" if due_date else ""
                return f"Task registered, {callsign}: '{task_title}'{due_str}. Added to active tactical radar."
            return f"Task noted, {callsign}: '{task_title}'."

        # 2B. List Pending Tasks: "What are my pending tasks?", "Show tasks", "List tasks"
        if re.search(r"\b(?:what\s+are\s+my\s+pending\s+tasks|pending\s+tasks|show\s+(?:my\s+)?tasks|list\s+(?:my\s+)?tasks|what\s+tasks\s+do\s+i\s+have)\b", lower):
            if db:
                tasks = db.get_tasks(completed=False)
                if tasks:
                    lines = []
                    for i, t in enumerate(tasks):
                        due_info = f" (Due: {t['due_date']})" if t.get('due_date') else ""
                        lines.append(f"[{i+1}] {t['title']}{due_info}")
                    return f"Pending Tasks on Tactical Radar for {callsign} ({len(tasks)} items):\n" + "\n".join(lines)
                else:
                    return f"You have no pending tasks on your tactical radar, {callsign}. All clear."
            return f"No pending tasks, {callsign}."

        # 2C. List Completed Tasks: "Show completed tasks", "List completed tasks"
        if re.search(r"\b(?:show\s+completed\s+tasks|list\s+completed\s+tasks|completed\s+tasks)\b", lower):
            if db:
                comp_tasks = db.get_tasks(completed=True)
                if comp_tasks:
                    lines = [f"[✓] {t['title']}" for t in comp_tasks[:10]]
                    return f"Completed Tasks Archive for {callsign} ({len(comp_tasks)} total):\n" + "\n".join(lines)
                else:
                    return f"No completed tasks recorded yet, {callsign}."
            return f"No completed tasks, {callsign}."

        # 2D. Mark Task Complete: "Mark my documentation task as complete", "Complete task [X]"
        task_comp_match = re.match(r"^(?:edith[,\s]+)?(?:mark\s+(?:my\s+|the\s+|task\s+)?(.+?)\s+(?:as\s+)?complete[d]?|complete\s+(?:my\s+|the\s+|task\s+)?(.+)|finish\s+(?:my\s+|the\s+|task\s+)?(.+))$", lower)
        if task_comp_match:
            raw_target = (task_comp_match.group(1) or task_comp_match.group(2) or task_comp_match.group(3)).strip().rstrip(".")
            # Clean up filler words: "my documentation task" -> "documentation"
            task_target = re.sub(r"\b(?:task|the|my|a|an)\b", "", raw_target).strip()
            if not task_target:
                task_target = raw_target
            if db:
                # Check if target is a number ID
                if task_target.isdigit():
                    t_id = int(task_target)
                    success = db.complete_task(t_id, True)
                    if success:
                        return f"Task #{t_id} marked as complete, {callsign}. Outstanding work."
                # Search by title pattern
                res = db.complete_task_by_title(task_target)
                if res:
                    return f"Task '{res['title']}' marked as complete, {callsign}. Outstanding work."
                else:
                    return f"I could not locate an active task matching '{raw_target}', {callsign}."
            return f"Task marked complete, {callsign}."

        # 2E. Delete Task: "Delete task [X]", "Remove task [X]"
        task_del_match = re.match(r"^(?:edith[,\s]+)?(?:delete\s+task|remove\s+task)\s+(.+)$", lower)
        if task_del_match:
            raw_target = task_del_match.group(1).strip().rstrip(".")
            task_target = re.sub(r"\b(?:task|the|my|a|an)\b", "", raw_target).strip()
            if not task_target:
                task_target = raw_target
            if db:
                if task_target.isdigit():
                    t_id = int(task_target)
                    success = db.delete_task(t_id)
                    if success:
                        return f"Task #{t_id} deleted from database, {callsign}."
                res = db.delete_task_by_title(task_target)
                if res:
                    return f"Task '{res['title']}' removed from database, {callsign}."
                else:
                    return f"No task found matching '{raw_target}', {callsign}."
            return f"Task deleted, {callsign}."

        # ============================================================
        # 3. REMINDERS (Milestone 3, Feature 4)
        # ============================================================

        # 3A. List Reminders: "What reminders do I have?", "Show reminders", "List reminders"
        if re.search(r"\b(?:what\s+reminders|show\s+(?:my\s+)?reminders|list\s+(?:my\s+)?reminders)\b", lower):
            if db:
                rems = db.get_reminders(active_only=True)
                if rems:
                    lines = []
                    for i, r in enumerate(rems):
                        try:
                            dt = datetime.datetime.fromisoformat(r['remind_at'])
                            t_str = dt.strftime("%b %d, %I:%M %p")
                        except Exception:
                            t_str = r['remind_at']
                        lines.append(f"[{i+1}] {r['title']} -> {t_str}")
                    return f"Scheduled Reminders for {callsign} ({len(rems)} active):\n" + "\n".join(lines)
                else:
                    return f"No upcoming reminders on file, {callsign}. Tactical schedule is clear."
            return f"No upcoming reminders, {callsign}."

        # 3B. Cancel / Delete Reminder: "Cancel reminder [X]", "Delete reminder [X]"
        rem_del_match = re.search(r"\b(?:cancel\s+reminder|delete\s+reminder|remove\s+reminder)\s+(.+)", lower)
        if rem_del_match:
            rem_target = rem_del_match.group(1).strip().rstrip(".")
            if db:
                if rem_target.isdigit():
                    r_id = int(rem_target)
                    success = db.delete_reminder(r_id)
                    if success:
                        return f"Reminder #{r_id} cancelled, {callsign}."
                res = db.delete_reminder_by_title(rem_target)
                if res:
                    return f"Reminder '{res['title']}' removed from schedule, {callsign}."
                else:
                    return f"No reminder matching '{rem_target}' was found, {callsign}."
            return f"Reminder cancelled, {callsign}."

        # 3C. Add Reminder with Time: "Remind me to finish documentation in 10 minutes", "Remind me at 18:00 to run diagnostics"
        # Match pattern: "remind me [at TIME] to [ACTION] [in/at TIME]"
        if re.search(r"\bremind\s+me\b", lower):
            # Check for prefix time: "remind me at 3pm to X"
            pref_time_match = re.search(r"\bremind\s+me\s+at\s+([0-9:apm\s]+?)\s+to\s+(.+)", lower)
            if pref_time_match:
                time_part = f"at {pref_time_match.group(1)}"
                action_part = clean[pref_time_match.start(2):].strip().rstrip(".")
                dt_obj, friendly = parse_time_expression(time_part)
            else:
                # Suffix time: "remind me to X in 10 minutes" or "remind me to X at 5pm"
                suff_match = re.search(r"\bremind\s+me\s+to\s+(.+?)(?:\s+(in\s+\d+\s*(?:minute|min|hour|hr|second|sec)s?|\bat\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?))\s*$", lower)
                if suff_match:
                    action_part = clean[suff_match.start(1):suff_match.end(1)].strip().rstrip(".")
                    time_part = suff_match.group(2)
                    dt_obj, friendly = parse_time_expression(time_part)
                else:
                    # Generic: "remind me to finish documentation"
                    gen_match = re.search(r"\bremind\s+me\s+to\s+(.+)", lower)
                    if gen_match:
                        action_part = clean[gen_match.start(1):].strip().rstrip(".")
                        # Default to 1 hour reminder
                        dt_obj = datetime.datetime.now() + datetime.timedelta(hours=1)
                        friendly = f"1 hour ({dt_obj.strftime('%I:%M %p')})"
                    else:
                        action_part = "Check system status"
                        dt_obj = datetime.datetime.now() + datetime.timedelta(hours=1)
                        friendly = "1 hour"

            if dt_obj:
                iso_time = dt_obj.isoformat()
                if db:
                    db.add_reminder(action_part, iso_time)
                return f"Reminder initialized, {callsign}: '{action_part}' scheduled for {friendly}."

        # ============================================================
        # 4. GREETINGS & IDENTITY
        # ============================================================
        if re.search(r"\b(hi|hello|hey|greetings|morning|afternoon|evening)\b", lower):
            now_hour = datetime.datetime.now().hour
            if now_hour < 12:
                time_greeting = "Good morning"
            elif now_hour < 18:
                time_greeting = "Good afternoon"
            else:
                time_greeting = "Good evening"

            greetings = [
                f"{time_greeting}, {callsign}. All local systems are online and operational. How can I assist you today?",
                f"Hello, {callsign}. EDITH online. Diagnostics are green. What is on the agenda?",
                f"Standing by, {callsign}. Secure local channel established. Ready for your command."
            ]
            return random.choice(greetings)

        if re.search(r"\b(who are you|what is edith|what does edith stand for|your name|your purpose)\b", lower):
            return (
                f"I am E.D.I.T.H. -- 'Even Dead, I'm The Hero'.\n\n"
                f"I am your personal, private desktop AI assistant designed for maximum security and zero cloud dependence. "
                f"Currently operating on Milestone 4.3: Safe Application, Website & Local File Search Suite. "
                f"Offline voice synthesis, speech recognition, long-term memory, tasks, reminders, and safe local file searching are fully operational."
            )

        # ============================================================
        # 5. HARDWARE STATUS & TELEMETRY
        # ============================================================
        if re.search(r"\b(status|diagnostics|health|hardware|system report|telemetry)\b", lower):
            cpu = telemetry.get("cpu_percent", "N/A")
            ram = telemetry.get("ram_percent", "N/A")
            ram_used = telemetry.get("ram_used_gb", "N/A")
            ram_total = telemetry.get("ram_total_gb", 16.0)
            battery = telemetry.get("battery_percent", "N/A")
            status = telemetry.get("status", "NOMINAL")
            uptime = telemetry.get("uptime", "00:00:00")

            return (
                f"Diagnostic Telemetry Report for {callsign}:\n"
                f"- Core Status: {status}\n"
                f"- CPU Load: {cpu}%\n"
                f"- Memory Footprint: {ram}% ({ram_used} GB / {ram_total} GB)\n"
                f"- Power Level: {battery}%\n"
                f"- Active Uptime: {uptime}\n"
                f"- Security Protocol: Localhost Isolated (Zero Cloud Leakage)"
            )

        if re.search(r"\b(cpu|ram|memory|battery)\b", lower):
            if "cpu" in lower:
                return f"Current CPU utilization is at {telemetry.get('cpu_percent', 'nominal')}%. Subsystems are idling efficiently."
            elif "ram" in lower or "memory" in lower:
                return (
                    f"Memory analysis: Using {telemetry.get('ram_used_gb', '0')} GB of {telemetry.get('ram_total_gb', '16')} GB total "
                    f"({telemetry.get('ram_percent', '0')}%). {telemetry.get('ram_available_gb', '12')} GB remains available for operations."
                )
            elif "battery" in lower or "power" in lower:
                return f"Power cell status: {telemetry.get('battery_percent', '100')}% ({telemetry.get('battery_status', 'Connected')})."

        # ============================================================
        # 6. TIME & DATE
        # ============================================================
        if re.search(r"\b(time|what time|clock)\b", lower):
            now_str = datetime.datetime.now().strftime("%I:%M:%S %p")
            return f"The current system time is {now_str}."

        if re.search(r"\b(date|what day|today)\b", lower):
            date_str = datetime.datetime.now().strftime("%A, %B %d, %Y")
            return f"Today is {date_str}."

        # ============================================================
        # 7. CAPABILITIES & HELP
        # ============================================================
        if re.search(r"\b(help|commands|capabilities|what can you do)\b", lower):
            return (
                f"E.D.I.T.H. Tactical Directives for {callsign}:\n"
                f"- App Launcher: 'Open Notepad', 'Launch Calculator', 'Open File Explorer', 'Start Paint', 'Open Task Manager'.\n"
                f"- Web Launcher: 'Open YouTube', 'Launch Google', 'Go to ChatGPT', 'Open Gmail', 'Take me to GitHub', 'Visit Wikipedia', 'Open Reddit', 'Go to Stack Overflow'.\n"
                f"- File Search: 'Find my PDF files', 'Search for resume', 'Find Project Report', 'Find images in Downloads', 'Find Python files', 'Search for files named budget', 'Find folders named Projects', 'Open result [N]', 'Open folder [N]'.\n"
                f"- Memory: 'Remember that...', 'What do you remember about [X]?', 'Show memories', 'Forget [X]'.\n"
                f"- Tasks: 'Add task [title]', 'Show pending tasks', 'Mark task [title] complete', 'Delete task [title]'.\n"
                f"- Reminders: 'Remind me to [title] in [N] minutes/hours', 'Show reminders', 'Cancel reminder [title]'.\n"
                f"- Telemetry: 'Status', 'CPU', 'RAM', 'Time', 'Date'.\n"
                f"- Voice: Full speech recognition via HUD microphone and offline Piper neural voice output.\n"
                f"- Security: 'Protocols', 'Clear'."
            )

        # ============================================================
        # 8. SECURITY & PROTOCOLS
        # ============================================================
        if re.search(r"\b(security|protocol|privacy|safe|offline)\b", lower):
            return (
                f"Security Assessment: Level 1 Alpha.\n"
                f"- Network Access: Blocked / Offline Mode Active\n"
                f"- Local Storage: Local SQLite repository (data/edith.db)\n"
                f"- Privacy Protection: Passwords and financial credentials blocked from memory storage\n"
                f"- External Telemetry: Disabled\n"
                f"- Destructive Command Execution: Hard restricted by approval gatekeeper."
            )

        # ============================================================
        # 9. MARVEL / STARK EASTER EGGS
        # ============================================================
        if re.search(r"\b(stark|tony|jarvis|friday|avengers|suit)\b", lower):
            return (
                f"Tony left big shoes to fill. As he always said: 'Part of the journey is the end.' "
                f"I am tuned specifically for you, {callsign}. How may I configure our protocols today?"
            )

        # ============================================================
        # 10. POLITE FALLBACK
        # ============================================================
        fallbacks = [
            f"Understood, {callsign}. Processing your query: '{clean}'. Local memory and tactical registries are updated.",
            f"Command received, {callsign}. All subsystems report normal parameters. Request acknowledged.",
            f"I have logged that in our local session, {callsign}. Standing by for your next instruction.",
            f"Acknowledged, {callsign}. Telemetry, tasks, and memory channels remain active and responsive."
        ]
        return random.choice(fallbacks)
