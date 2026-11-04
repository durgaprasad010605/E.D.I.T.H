"""
Local SQLite Database Manager for E.D.I.T.H. (Milestone 3)
Manages persistent local history, user preferences, personal memories/notes,
tasks, reminders, and audit logs with safe migrations and zero cloud dependencies.
"""
import sqlite3
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

class DatabaseManager:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Create tables if they do not exist and apply safe migrations."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Chat history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    text TEXT NOT NULL,
                    status TEXT DEFAULT 'delivered'
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_id ON messages (id)")

            # 2. System audit logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    event TEXT NOT NULL,
                    details TEXT
                )
            """)

            # 3. Key-value settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # 4. Tasks table (Milestone 3)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    completed INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    due_date TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_completed ON tasks (completed)")

            # Safe migration: ensure completed_at column exists in tasks if created prior to M3
            cursor.execute("PRAGMA table_info(tasks)")
            columns = [row["name"] for row in cursor.fetchall()]
            if "completed_at" not in columns:
                cursor.execute("ALTER TABLE tasks ADD COLUMN completed_at TEXT")

            # 5. Personal Memories / Notes table (Milestone 3)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_created ON memories (created_at)")

            # 6. Reminders table (Milestone 3)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    remind_at TEXT NOT NULL,
                    is_completed INTEGER DEFAULT 0,
                    is_notified INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_reminders_remind_at ON reminders (remind_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_reminders_status ON reminders (is_completed, is_notified)")

            conn.commit()

    # ============================================================
    # CHAT HISTORY METHODS (Feature 1)
    # ============================================================
    def log_message(self, sender: str, text: str) -> int:
        """Store a chat message with deduplication protection."""
        now = datetime.datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Prevent exact duplicate message insertion within 2 seconds
            cursor.execute(
                "SELECT id, timestamp, text FROM messages WHERE sender = ? ORDER BY id DESC LIMIT 1",
                (sender,)
            )
            last = cursor.fetchone()
            if last and last["text"] == text:
                try:
                    last_time = datetime.datetime.fromisoformat(last["timestamp"])
                    if (datetime.datetime.now() - last_time).total_seconds() < 2.0:
                        return last["id"]
                except Exception:
                    pass

            cursor.execute(
                "INSERT INTO messages (timestamp, sender, text) VALUES (?, ?, ?)",
                (now, sender, text)
            )
            conn.commit()
            return cursor.lastrowid

    def get_recent_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent conversation history ordered chronologically."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, timestamp, sender, text, status FROM messages ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in reversed(rows)]

    def clear_messages(self):
        """Wipe conversation history upon user request."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages")
            conn.commit()

    # ============================================================
    # AUDIT LOGS & SETTINGS METHODS
    # ============================================================
    def log_audit(self, level: str, event: str, details: str = ""):
        """Record system diagnostic or security events."""
        now = datetime.datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO audit_logs (timestamp, level, event, details) VALUES (?, ?, ?, ?)",
                (now, level, event, details)
            )
            conn.commit()

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Fetch a persistent setting."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str):
        """Save a persistent setting."""
        now = datetime.datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
                (key, value, now)
            )
            conn.commit()

    # ============================================================
    # PERSONAL MEMORY METHODS (Feature 2)
    # ============================================================
    def add_memory(self, content: str, category: str = "general") -> int:
        """Save a discrete user memory/note."""
        now = datetime.datetime.now().isoformat()
        content = content.strip()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO memories (content, category, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (content, category, now, now)
            )
            conn.commit()
            return cursor.lastrowid

    def get_memories(self, search: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve memories, optionally filtered by keyword search."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if search and search.strip():
                pattern = f"%{search.strip()}%"
                cursor.execute(
                    "SELECT id, content, category, created_at, updated_at FROM memories WHERE content LIKE ? ORDER BY id DESC LIMIT ?",
                    (pattern, limit)
                )
            else:
                cursor.execute(
                    "SELECT id, content, category, created_at, updated_at FROM memories ORDER BY id DESC LIMIT ?",
                    (limit,)
                )
            return [dict(row) for row in cursor.fetchall()]

    def get_memory_by_id(self, memory_id: int) -> Optional[Dict[str, Any]]:
        """Fetch single memory by primary key."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, content, category, created_at, updated_at FROM memories WHERE id = ?", (memory_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_memory(self, memory_id: int, content: str, category: Optional[str] = None) -> bool:
        """Update existing memory content."""
        now = datetime.datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if category:
                cursor.execute(
                    "UPDATE memories SET content = ?, category = ?, updated_at = ? WHERE id = ?",
                    (content.strip(), category, now, memory_id)
                )
            else:
                cursor.execute(
                    "UPDATE memories SET content = ?, updated_at = ? WHERE id = ?",
                    (content.strip(), now, memory_id)
                )
            conn.commit()
            return cursor.rowcount > 0

    def delete_memory(self, memory_id: int) -> bool:
        """Delete memory by primary key."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()
            return cursor.rowcount > 0

    def delete_memory_by_content(self, search_term: str) -> int:
        """Delete memories matching a search keyword."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            pattern = f"%{search_term.strip()}%"
            cursor.execute("DELETE FROM memories WHERE content LIKE ?", (pattern,))
            conn.commit()
            return cursor.rowcount

    # ============================================================
    # TASK MANAGEMENT METHODS (Feature 3)
    # ============================================================
    def add_task(self, title: str, due_date: Optional[str] = None) -> int:
        """Register a new task with optional due date."""
        now = datetime.datetime.now().isoformat()
        title = title.strip()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tasks (title, completed, created_at, due_date) VALUES (?, 0, ?, ?)",
                (title, now, due_date)
            )
            conn.commit()
            return cursor.lastrowid

    def get_tasks(self, completed: Optional[bool] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve tasks, optionally filtered by completion state."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if completed is None:
                cursor.execute(
                    "SELECT id, title, completed, created_at, completed_at, due_date FROM tasks ORDER BY completed ASC, id DESC LIMIT ?",
                    (limit,)
                )
            else:
                comp_val = 1 if completed else 0
                cursor.execute(
                    "SELECT id, title, completed, created_at, completed_at, due_date FROM tasks WHERE completed = ? ORDER BY id DESC LIMIT ?",
                    (comp_val, limit)
                )
            return [dict(row) for row in cursor.fetchall()]

    def get_task_by_id(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Fetch single task by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, completed, created_at, completed_at, due_date FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_task(self, task_id: int, title: str, due_date: Optional[str] = None) -> bool:
        """Update task details."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tasks SET title = ?, due_date = ? WHERE id = ?",
                (title.strip(), due_date, task_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def complete_task(self, task_id: int, completed: bool = True) -> bool:
        """Mark task as completed or reopen it."""
        now = datetime.datetime.now().isoformat() if completed else None
        comp_val = 1 if completed else 0
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tasks SET completed = ?, completed_at = ? WHERE id = ?",
                (comp_val, now, task_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def complete_task_by_title(self, title_pattern: str) -> Optional[Dict[str, Any]]:
        """Find pending task matching pattern and mark completed."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            pattern = f"%{title_pattern.strip()}%"
            cursor.execute(
                "SELECT id, title FROM tasks WHERE completed = 0 AND title LIKE ? ORDER BY id DESC LIMIT 1",
                (pattern,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            task_id = row["id"]
            now = datetime.datetime.now().isoformat()
            cursor.execute("UPDATE tasks SET completed = 1, completed_at = ? WHERE id = ?", (now, task_id))
            conn.commit()
            return dict(row)

    def delete_task(self, task_id: int) -> bool:
        """Delete task by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0

    def delete_task_by_title(self, title_pattern: str) -> Optional[Dict[str, Any]]:
        """Delete task matching title pattern."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            pattern = f"%{title_pattern.strip()}%"
            cursor.execute(
                "SELECT id, title FROM tasks WHERE title LIKE ? ORDER BY id DESC LIMIT 1",
                (pattern,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            task_id = row["id"]
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            return dict(row)

    # ============================================================
    # REMINDERS METHODS (Feature 4)
    # ============================================================
    def add_reminder(self, title: str, remind_at: str) -> int:
        """Register a new reminder."""
        now = datetime.datetime.now().isoformat()
        title = title.strip()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO reminders (title, remind_at, is_completed, is_notified, created_at) VALUES (?, ?, 0, 0, ?)",
                (title, remind_at, now)
            )
            conn.commit()
            return cursor.lastrowid

    def get_reminders(self, active_only: bool = False, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve reminders."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if active_only:
                cursor.execute(
                    "SELECT id, title, remind_at, is_completed, is_notified, created_at FROM reminders WHERE is_completed = 0 ORDER BY remind_at ASC LIMIT ?",
                    (limit,)
                )
            else:
                cursor.execute(
                    "SELECT id, title, remind_at, is_completed, is_notified, created_at FROM reminders ORDER BY is_completed ASC, remind_at ASC LIMIT ?",
                    (limit,)
                )
            return [dict(row) for row in cursor.fetchall()]

    def get_due_reminders(self) -> List[Dict[str, Any]]:
        """Query reminders whose remind_at timestamp has passed and have not yet been notified."""
        now = datetime.datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, title, remind_at, is_completed, is_notified, created_at FROM reminders WHERE remind_at <= ? AND is_completed = 0 AND is_notified = 0 ORDER BY remind_at ASC",
                (now,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def mark_reminder_notified(self, reminder_id: int) -> bool:
        """Flag reminder as notified to avoid duplicate notifications."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE reminders SET is_notified = 1 WHERE id = ?", (reminder_id,))
            conn.commit()
            return cursor.rowcount > 0

    def complete_reminder(self, reminder_id: int, completed: bool = True) -> bool:
        """Mark reminder as completed/dismissed."""
        comp_val = 1 if completed else 0
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE reminders SET is_completed = ?, is_notified = 1 WHERE id = ?", (comp_val, reminder_id))
            conn.commit()
            return cursor.rowcount > 0

    def delete_reminder(self, reminder_id: int) -> bool:
        """Delete reminder by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
            conn.commit()
            return cursor.rowcount > 0

    def delete_reminder_by_title(self, title_pattern: str) -> Optional[Dict[str, Any]]:
        """Delete reminder by title pattern."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            pattern = f"%{title_pattern.strip()}%"
            cursor.execute(
                "SELECT id, title FROM reminders WHERE title LIKE ? ORDER BY id DESC LIMIT 1",
                (pattern,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            rem_id = row["id"]
            cursor.execute("DELETE FROM reminders WHERE id = ?", (rem_id,))
            conn.commit()
            return dict(row)
