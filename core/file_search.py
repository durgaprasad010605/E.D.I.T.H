"""
Safe Local File & Folder Search for E.D.I.T.H. (Milestone 4.3)
Enforces strict read-only searching within verified Windows user directories
(Desktop, Documents, Downloads, Pictures, Videos, Music) and explicitly requested project directories.
Never executes arbitrary commands, never modifies or deletes files,
never scans arbitrary drive roots or system directories, and strictly blocks
binary execution from search results.
"""
import os
import re
import stat
import logging
import datetime
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set

logger = logging.getLogger("EDITH.FileSearch")

# ==============================================================================
# APPROVED SEARCH SCOPES & EXTENSION ALIASES
# ==============================================================================
FILE_TYPE_ALIASES: Dict[str, List[str]] = {
    "pdf": [".pdf"],
    "python": [".py", ".pyw"],
    "py": [".py"],
    "image": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".ico"],
    "images": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".ico"],
    "picture": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".ico"],
    "pictures": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".ico"],
    "photo": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".ico"],
    "photos": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".ico"],
    "video": [".mp4", ".mkv", ".mov", ".avi", ".wmv", ".webm"],
    "videos": [".mp4", ".mkv", ".mov", ".avi", ".wmv", ".webm"],
    "movie": [".mp4", ".mkv", ".mov", ".avi", ".wmv", ".webm"],
    "movies": [".mp4", ".mkv", ".mov", ".avi", ".wmv", ".webm"],
    "audio": [".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"],
    "music": [".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"],
    "song": [".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"],
    "songs": [".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"],
    "document": [".docx", ".doc", ".pdf", ".rtf", ".odt", ".txt"],
    "documents": [".docx", ".doc", ".pdf", ".rtf", ".odt", ".txt"],
    "doc": [".docx", ".doc"],
    "docs": [".docx", ".doc"],
    "word": [".docx", ".doc"],
    "spreadsheet": [".xlsx", ".xls", ".csv"],
    "spreadsheets": [".xlsx", ".xls", ".csv"],
    "excel": [".xlsx", ".xls", ".csv"],
    "csv": [".csv"],
    "presentation": [".pptx", ".ppt"],
    "presentations": [".pptx", ".ppt"],
    "powerpoint": [".pptx", ".ppt"],
    "ppt": [".pptx", ".ppt"],
    "text": [".txt", ".md", ".log"],
    "txt": [".txt"],
    "archive": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "zip": [".zip"]
}

# Directories that must NEVER be traversed
EXCLUDED_DIR_NAMES: Set[str] = {
    "appdata", "local", "roaming", "program files", "program files (x86)",
    "windows", "system32", "syswow64", "$recycle.bin", "system volume information",
    "node_modules", "__pycache__", "venv", ".venv", "env", ".env", "site-packages",
    ".git", ".cache", "temp", "tmp", ".gemini", ".vscode", ".idea"
}

# Executable file extensions blocked from being launched from search results
BLOCKED_EXEC_EXTENSIONS: Set[str] = {
    ".exe", ".bat", ".cmd", ".vbs", ".ps1", ".msi", ".com", ".scr", ".pif",
    ".reg", ".jar", ".cpl", ".hta", ".wsf", ".sh"
}

def resolve_windows_user_roots() -> Dict[str, Path]:
    """
    Dynamically resolve actual Windows user directories using the Windows Registry
    (User Shell Folders) with fallback to Path.home(). Handles OneDrive redirection cleanly.
    """
    roots: Dict[str, Path] = {}
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as key:
            mapping = {
                "desktop": "Desktop",
                "documents": "Personal",
                "pictures": "My Pictures",
                "music": "My Music",
                "videos": "My Video",
                "downloads": "{374DE290-123F-4565-9164-39C4925E467B}"
            }
            for name, reg_val in mapping.items():
                try:
                    val, _ = winreg.QueryValueEx(key, reg_val)
                    expanded = os.path.expandvars(val)
                    p = Path(expanded).resolve()
                    try:
                        if p.exists() and p.is_dir():
                            roots[name] = p
                    except PermissionError:
                        roots[name] = p
                except Exception:
                    pass
    except Exception:
        pass

    # Fallback to standard user home subdirectories
    home = Path.home().resolve()
    fallbacks = {
        "desktop": home / "Desktop",
        "documents": home / "Documents",
        "downloads": home / "Downloads",
        "pictures": home / "Pictures",
        "music": home / "Music",
        "videos": home / "Videos"
    }
    for name, path in fallbacks.items():
        if name not in roots and path.exists() and path.is_dir():
            roots[name] = path.resolve()

    return roots


class FileSearchEngine:
    """
    Safe Local File & Folder Search Engine.
    Operates strictly read-only and confines searches to approved Windows user directories.
    """

    PAGE_SIZE = 10
    MAX_SEARCH_RESULTS = 100
    MAX_SEARCH_DEPTH = 6

    def __init__(self, db: Optional[Any] = None, custom_roots: Optional[Dict[str, Path]] = None):
        self.db = db
        self.approved_roots = custom_roots if custom_roots is not None else resolve_windows_user_roots()
        # Project directory (searched only when explicitly requested)
        self.project_dir = Path(__file__).resolve().parent.parent

        self.last_results: List[Dict[str, Any]] = []
        self.last_query: str = ""
        self.current_page: int = 0

    def get_search_roots(self) -> Dict[str, str]:
        """Return names and resolved paths of authorized search roots."""
        result = {k: str(v) for k, v in self.approved_roots.items()}
        result["edith"] = str(self.project_dir)
        return result

    def describe_file_type(self, name: str, is_dir: bool) -> str:
        """Return human-friendly description of file type based on extension."""
        if is_dir:
            return "Folder"
        ext = Path(name).suffix.lower()
        descriptions = {
            ".pdf": "PDF Document",
            ".py": "Python Source Code",
            ".pyw": "Python GUI Script",
            ".txt": "Text Document",
            ".md": "Markdown Document",
            ".docx": "Word Document",
            ".doc": "Word Document",
            ".xlsx": "Excel Spreadsheet",
            ".xls": "Excel Spreadsheet",
            ".csv": "CSV Data File",
            ".pptx": "PowerPoint Presentation",
            ".ppt": "PowerPoint Presentation",
            ".png": "PNG Image",
            ".jpg": "JPEG Image",
            ".jpeg": "JPEG Image",
            ".gif": "GIF Animation",
            ".bmp": "Bitmap Image",
            ".webp": "WebP Image",
            ".svg": "Vector Graphic",
            ".mp4": "MP4 Video",
            ".mkv": "MKV Video",
            ".mov": "QuickTime Video",
            ".avi": "AVI Video",
            ".mp3": "MP3 Audio",
            ".wav": "WAV Audio",
            ".flac": "FLAC Audio",
            ".zip": "ZIP Archive",
            ".rar": "RAR Archive",
            ".7z": "7-Zip Archive",
            ".json": "JSON Data File",
            ".html": "HTML Web Page",
            ".css": "CSS Stylesheet",
            ".js": "JavaScript File"
        }
        return descriptions.get(ext, f"{ext.upper()[1:]} File" if ext else "File")

    def _is_safe_to_traverse(self, entry: os.DirEntry) -> bool:
        """Check whether a directory entry should be traversed safely."""
        name_lower = entry.name.lower()

        # 1. Skip hidden entries (starting with .)
        if name_lower.startswith("."):
            return False

        # 2. Skip excluded system and cache directories
        if name_lower in EXCLUDED_DIR_NAMES:
            return False

        # 3. Skip symbolic links and junctions to avoid infinite loops or escaping approved roots
        try:
            if entry.is_symlink():
                return False
        except (OSError, PermissionError):
            return False

        # 4. Check Windows hidden or system file attributes
        try:
            st = entry.stat(follow_symlinks=False)
            if hasattr(st, "st_file_attributes"):
                # FILE_ATTRIBUTE_HIDDEN = 0x2, FILE_ATTRIBUTE_SYSTEM = 0x4
                if st.st_file_attributes & (stat.FILE_ATTRIBUTE_HIDDEN | 0x4):
                    return False
        except (OSError, PermissionError):
            return False

        return True

    def search(
        self,
        keyword: Optional[str] = None,
        extension: Optional[str] = None,
        target_type: str = "any",  # "any", "file", "folder"
        scope: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute safe local search across approved directories.
        Guarantees:
        - Read-only operations.
        - Graceful handling of inaccessible or missing directories.
        - Never traverses system directories or hidden items.
        - Never escapes approved search roots.
        """
        results: List[Dict[str, Any]] = []

        # Determine target search roots
        search_dirs: List[Path] = []
        if scope:
            clean_scope = scope.lower().strip()
            if clean_scope in ("edith", "project"):
                search_dirs.append(self.project_dir)
            elif clean_scope in self.approved_roots:
                search_dirs.append(self.approved_roots[clean_scope])
            else:
                # If scope is not recognized, search default user roots
                search_dirs = list(self.approved_roots.values())
        else:
            # Default to all approved user roots (project is only searched if requested)
            search_dirs = list(self.approved_roots.values())

        # Normalize keyword and extensions
        kw_clean = keyword.lower().strip() if keyword else None
        exts_clean: Optional[Set[str]] = None
        if extension:
            if isinstance(extension, (list, set)):
                exts_clean = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in extension}
            else:
                e = extension.lower().strip()
                exts_clean = {e if e.startswith(".") else f".{e}"}

        # Breadth-first traversal with depth tracking
        for root_dir in search_dirs:
            if not root_dir.exists() or not root_dir.is_dir():
                continue

            # Queue of (current_dir_path, current_depth)
            queue = [(root_dir, 0)]

            while queue and len(results) < self.MAX_SEARCH_RESULTS:
                current_path, depth = queue.pop(0)

                try:
                    with os.scandir(current_path) as scanner:
                        for entry in scanner:
                            if len(results) >= self.MAX_SEARCH_RESULTS:
                                break

                            try:
                                is_dir = entry.is_dir(follow_symlinks=False)
                            except (OSError, PermissionError):
                                continue

                            entry_name_lower = entry.name.lower()

                            # Match candidate
                            matches = True

                            # 1. Target type filter
                            if target_type == "folder" and not is_dir:
                                matches = False
                            elif target_type == "file" and is_dir:
                                matches = False

                            # 2. Extension filter
                            if matches and exts_clean:
                                if is_dir:
                                    matches = False
                                else:
                                    entry_ext = Path(entry.name).suffix.lower()
                                    if entry_ext not in exts_clean:
                                        matches = False

                            # 3. Keyword filter (partial substring match)
                            if matches and kw_clean:
                                if kw_clean not in entry_name_lower:
                                    matches = False

                            # Add matching item
                            if matches and not entry_name_lower.startswith("."):
                                try:
                                    st = entry.stat(follow_symlinks=False)
                                    mod_time = datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")
                                    type_desc = self.describe_file_type(entry.name, is_dir)
                                    item_path = Path(entry.path).resolve()

                                    # Security check: Ensure item is inside the approved root
                                    try:
                                        item_path.relative_to(root_dir.resolve())
                                    except ValueError:
                                        continue

                                    results.append({
                                        "name": entry.name,
                                        "path": str(item_path),
                                        "is_dir": is_dir,
                                        "size_bytes": st.st_size if not is_dir else 0,
                                        "modified_at": mod_time,
                                        "type_desc": type_desc,
                                        "folder_location": str(item_path.parent)
                                    })
                                except (OSError, PermissionError):
                                    pass

                            # Enqueue subdirectories if depth allows
                            if is_dir and depth < self.MAX_SEARCH_DEPTH:
                                if self._is_safe_to_traverse(entry):
                                    queue.append((Path(entry.path), depth + 1))

                except (PermissionError, FileNotFoundError, OSError):
                    # Inaccessible directory: skip safely
                    continue

        self.last_results = results
        self.current_page = 0
        self.last_query = f"{keyword or ''} {extension or ''}".strip()

        # Audit log into SQLite database
        if self.db:
            self.db.log_audit("INFO", "FILE_SEARCH", f"Found {len(results)} items for query '{self.last_query}'")

        return results

    def get_current_page_results(self) -> Tuple[List[Dict[str, Any]], int, int, int]:
        """
        Return results for the current page.
        Returns (items_list, start_idx, end_idx, total_count).
        """
        total = len(self.last_results)
        if total == 0:
            return [], 0, 0, 0

        start = self.current_page * self.PAGE_SIZE
        if start >= total:
            self.current_page = max(0, (total - 1) // self.PAGE_SIZE)
            start = self.current_page * self.PAGE_SIZE

        end = min(start + self.PAGE_SIZE, total)
        return self.last_results[start:end], start + 1, end, total

    def format_results_for_chat(self, callsign: str = "Boss") -> str:
        """Format current search page results into a clean, futuristic HUD text block."""
        items, start_idx, end_idx, total = self.get_current_page_results()
        if total == 0:
            return f"No matching files or folders found, {callsign}. Local registers report zero items."

        lines = [
            f"Search Results for {callsign} (Showing {start_idx}-{end_idx} of {total}):"
        ]
        for i, item in enumerate(items, start=start_idx):
            icon = "[Folder]" if item["is_dir"] else "[File]"
            # Format folder path cleanly
            folder_clean = item["folder_location"]
            # Shorten user path for clean display
            home_str = str(Path.home())
            if folder_clean.startswith(home_str):
                folder_clean = "~" + folder_clean[len(home_str):]

            lines.append(
                f"[{i}] {icon} {item['name']}\n"
                f"    Type: {item['type_desc']} | Modified: {item['modified_at']}\n"
                f"    Location: {folder_clean}"
            )

        # Action directives footer
        footer = []
        if end_idx < total:
            footer.append("Say 'Show more results' or 'Next page' to view the next 10 items.")
        footer.append("To open a file, say 'Open result [number]' | To view in Explorer, say 'Open folder [number]'.")

        return "\n".join(lines) + "\n\n" + "\n".join(footer)

    def next_page(self, callsign: str = "Boss") -> str:
        """Advance to the next page of results and return the formatted block."""
        total = len(self.last_results)
        if total == 0:
            return f"No active search session, {callsign}. Please perform a search first."

        max_page = (total - 1) // self.PAGE_SIZE
        if self.current_page >= max_page:
            return f"You are already viewing the final results ({total} items total), {callsign}."

        self.current_page += 1
        return self.format_results_for_chat(callsign)

    def open_result(self, index: int, open_folder: bool = False, callsign: str = "Boss") -> Tuple[bool, str]:
        """
        Safely open an individual search result item or its containing folder.
        Guarantees:
        - Only items in the recent search results can be opened.
        - Path must be validated to reside inside approved roots (prevents path traversal).
        - Executable/script files (.exe, .bat, etc.) are strictly blocked from execution.
        - Uses os.startfile on Windows (associated desktop app) with shell=False.
        """
        if not self.last_results:
            return False, f"No recent search results on file, {callsign}. Please perform a search first."

        if index < 1 or index > len(self.last_results):
            return False, f"Invalid result index #{index}, {callsign}. Please choose between 1 and {len(self.last_results)}."

        item = self.last_results[index - 1]
        target_path = Path(item["folder_location"] if open_folder else item["path"]).resolve()

        # Security check: Ensure path exists
        if not target_path.exists():
            return False, f"Notice: Target '{item['name']}' no longer exists on disk, {callsign}."

        # Security check: Ensure target resides inside an approved search root
        is_safe_location = False
        allowed_locations = list(self.approved_roots.values()) + [self.project_dir]
        for allowed in allowed_locations:
            try:
                target_path.relative_to(allowed.resolve())
                is_safe_location = True
                break
            except ValueError:
                continue

        if not is_safe_location:
            logger.warning(f"Security Alert: Path '{target_path}' attempted to escape approved roots.")
            return False, f"Security Protocol Notice: Target path lies outside authorized roots, {callsign}."

        # Security check: Disallow executing binary executables or scripts
        if not open_folder and not item["is_dir"]:
            ext = target_path.suffix.lower()
            if ext in BLOCKED_EXEC_EXTENSIONS:
                return False, (
                    f"Security Protocol Notice: Direct execution of '{ext}' executable or script files is blocked, {callsign}. "
                    f"You may use 'Open folder {index}' to inspect its folder in File Explorer."
                )

        try:
            if open_folder or item["is_dir"]:
                # Open directory in File Explorer
                os.startfile(str(target_path))
                if self.db:
                    self.db.log_audit("INFO", "FOLDER_OPEN", f"Opened folder '{target_path}'")
                return True, f"Opening folder for '{item['name']}' in File Explorer, {callsign}."
            else:
                # Open file in its default associated Windows application
                os.startfile(str(target_path))
                if self.db:
                    self.db.log_audit("INFO", "FILE_OPEN", f"Opened file '{item['name']}' ({item['type_desc']})")
                return True, f"Opening '{item['name']}' with default application, {callsign}."

        except Exception as e:
            err = f"Failed to open '{item['name']}': {e}"
            logger.error(err)
            return False, f"Notice: Could not open {item['name']}, {callsign}. {e}"

    def parse_query(self, user_input: str) -> Optional[Dict[str, Any]]:
        """
        Parse natural-language search directives.
        Extracts keyword, extension, target_type, and scope.
        """
        lower = user_input.strip().lower()

        # Check search triggers
        search_match = re.match(r"^(?:edith[,\s]+)?(?:please\s+)?(?:can\s+you\s+)?(?:find|search\s+for|search|locate|look\s+for|where\s+(?:is|are))\b(?:\s+(.+))?$", lower)
        if not search_match:
            return None

        raw_query = search_match.group(1)
        if not raw_query or not raw_query.strip():
            return {"keyword": None, "extension": None, "target_type": "any", "scope": None}

        query = raw_query.strip().rstrip(".!?")

        # 1. Detect Scope: "in Downloads", "on Desktop", "in Documents", "in EDITH"
        scope = None
        scope_match = re.search(r"\b(?:in|on|inside)\s+(desktop|documents|downloads|pictures|videos|music|edith|project)\b", query)
        if scope_match:
            scope = scope_match.group(1)
            # Remove scope expression from query
            query = query[:scope_match.start()] + query[scope_match.end():]
            query = query.strip()

        # 2. Detect Target Type: "folders named ...", "folder ...", "directory ..."
        target_type = "any"
        if re.search(r"\b(folders|folder|directories|directory)\b", query):
            target_type = "folder"
            query = re.sub(r"\b(?:folders\s+named|folder\s+named|directories\s+named|directory\s+named|folders|folder|directories|directory)\b", "", query).strip()
        elif re.search(r"\b(files\s+named|file\s+named)\b", query):
            target_type = "file"
            query = re.sub(r"\b(?:files\s+named|file\s+named)\b", "", query).strip()

        # 3. Detect Extension from keyword or file type terms
        extension = None

        # Check for explicit extensions: *.pdf, .docx, or extension words
        ext_match = re.search(r"\b\.([a-zA-Z0-9]{1,5})\b", query)
        if ext_match:
            extension = f".{ext_match.group(1)}"
            query = query[:ext_match.start()] + query[ext_match.end():]
            query = query.strip()
        else:
            # Check known extension alias keys
            for alias, exts in FILE_TYPE_ALIASES.items():
                pattern = rf"\b{re.escape(alias)}(?:\s+files|\s+file)?\b"
                if re.search(pattern, query):
                    extension = exts
                    # Remove the alias phrase
                    query = re.sub(pattern, "", query).strip()
                    break

        # 4. Clean remaining filler words from keyword
        clean_kw = re.sub(r"^(?:my|the|a|an|all|any)\b\s*", "", query, flags=re.IGNORECASE).strip()
        clean_kw = re.sub(r"\s*(?:files|file)$", "", clean_kw, flags=re.IGNORECASE).strip()
        if clean_kw.lower() in ("my", "the", "a", "an", "all", "any", "file", "files"):
            clean_kw = ""
        clean_kw = clean_kw.strip("\"' ")

        keyword = clean_kw if clean_kw else None

        return {
            "keyword": keyword,
            "extension": extension,
            "target_type": target_type,
            "scope": scope
        }

    def handle_command(self, user_input: str, callsign: str = "Boss") -> Tuple[bool, str]:
        """
        Process search queries, pagination, and open result commands.
        Returns (is_handled: bool, reply: str).
        """
        clean = user_input.strip()
        lower = clean.lower()

        # 1. Open Result Directives: "open result 1", "open file 2", "open folder 1"
        open_match = re.match(r"^(?:edith[,\s]+)?(?:please\s+)?(?:can\s+you\s+)?open\s+(result|file|item|folder)\s+(\d+)\b", lower)
        if open_match:
            action_type = open_match.group(1)
            idx = int(open_match.group(2))
            is_folder = action_type == "folder"
            success, msg = self.open_result(idx, open_folder=is_folder, callsign=callsign)
            return True, msg

        # Alternative folder open phrasing: "open folder for result 1" or "open folder 1"
        f_match = re.match(r"^(?:edith[,\s]+)?(?:please\s+)?(?:can\s+you\s+)?(?:open\s+folder\s+(?:for\s+)?(?:result\s+)?|explore\s+(?:result\s+)?|view\s+folder\s+)(\d+)\b", lower)
        if f_match:
            idx = int(f_match.group(1))
            success, msg = self.open_result(idx, open_folder=True, callsign=callsign)
            return True, msg

        # 2. Pagination Directives: "show more results", "next page", "more results"
        if re.search(r"\b(?:show\s+more\s+results|next\s+page\s+of\s+results|next\s+page|more\s+results|next\s+results)\b", lower):
            if self.last_results:
                return True, self.next_page(callsign)
            return True, f"No previous search results to paginate, {callsign}."

        # 3. Parse File Search Query
        parsed = self.parse_query(clean)
        if not parsed:
            return False, ""

        # Case: User just said "find" or "search" without any query
        if not parsed["keyword"] and not parsed["extension"]:
            roots_str = ", ".join(self.approved_roots.keys()).title()
            return True, (
                f"Please specify a filename, extension, or topic to search, {callsign}. "
                f"For example: 'Find my PDF files', 'Search for budget', or 'Find images in Downloads'. "
                f"Currently monitored: {roots_str}."
            )

        # Execute search
        results = self.search(
            keyword=parsed["keyword"],
            extension=parsed["extension"],
            target_type=parsed["target_type"],
            scope=parsed["scope"]
        )

        return True, self.format_results_for_chat(callsign)
