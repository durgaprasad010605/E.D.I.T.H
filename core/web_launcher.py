"""
Safe Website Launcher for E.D.I.T.H. (Milestone 4.2)
Enforces a strict, hardcoded allowlist of approved HTTPS websites.
Opens approved websites strictly in the user's default browser via Python's webbrowser module.
Never evaluates arbitrary URLs, never passes user input to a shell,
and strictly blocks URL shorteners, IP addresses, unknown domains, or HTTP links.
"""
import re
import logging
import webbrowser
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("EDITH.WebLauncher")

# ==============================================================================
# STRICT WEBSITE ALLOWLIST (Milestone 4.2 Approved Websites)
# ==============================================================================
APPROVED_WEBSITES: Dict[str, Dict[str, Any]] = {
    "google": {
        "display_name": "Google",
        "url": "https://www.google.com/",
        "description": "Google Search Engine",
        "aliases": [
            "google",
            "google search",
            "google.com",
            "search google",
            "https://www.google.com/",
            "https://www.google.com",
            "https://google.com"
        ]
    },
    "youtube": {
        "display_name": "YouTube",
        "url": "https://www.youtube.com/",
        "description": "YouTube Video Platform",
        "aliases": [
            "youtube",
            "you tube",
            "yt",
            "youtube.com",
            "https://www.youtube.com/",
            "https://www.youtube.com",
            "https://youtube.com"
        ]
    },
    "chatgpt": {
        "display_name": "ChatGPT",
        "url": "https://chatgpt.com/",
        "description": "OpenAI ChatGPT Interface",
        "aliases": [
            "chatgpt",
            "chat gpt",
            "openai",
            "openai chatgpt",
            "chatgpt.com",
            "https://chatgpt.com/",
            "https://chatgpt.com"
        ]
    },
    "wikipedia": {
        "display_name": "Wikipedia",
        "url": "https://www.wikipedia.org/",
        "description": "Wikipedia Free Encyclopedia",
        "aliases": [
            "wikipedia",
            "wiki",
            "wikipedia.org",
            "https://www.wikipedia.org/",
            "https://www.wikipedia.org",
            "https://wikipedia.org"
        ]
    },
    "gmail": {
        "display_name": "Gmail",
        "url": "https://mail.google.com/",
        "description": "Google Mail",
        "aliases": [
            "gmail",
            "google mail",
            "mail.google.com",
            "my email",
            "email",
            "my mail",
            "mail",
            "https://mail.google.com/",
            "https://mail.google.com"
        ]
    },
    "github": {
        "display_name": "GitHub",
        "url": "https://github.com/",
        "description": "GitHub Software Repository",
        "aliases": [
            "github",
            "git hub",
            "github.com",
            "https://github.com/",
            "https://github.com"
        ]
    },
    "reddit": {
        "display_name": "Reddit",
        "url": "https://www.reddit.com/",
        "description": "Reddit Discussion Platform",
        "aliases": [
            "reddit",
            "reddit.com",
            "https://www.reddit.com/",
            "https://www.reddit.com"
        ]
    },
    "stackoverflow": {
        "display_name": "Stack Overflow",
        "url": "https://stackoverflow.com/",
        "description": "Stack Overflow Developer Community",
        "aliases": [
            "stack overflow",
            "stackoverflow",
            "stack over flow",
            "stackoverflow.com",
            "https://stackoverflow.com/",
            "https://stackoverflow.com"
        ]
    }
}

# Known common website identifiers used to classify intent as web navigation
COMMON_WEB_INDICATORS = {
    "facebook", "fb", "twitter", "x.com", "instagram", "insta", "amazon",
    "netflix", "tiktok", "linkedin", "twitch", "discord", "spotify",
    "bing", "yahoo", "duckduckgo", "ebay", "pinterest", "hulu", "disney"
}

class WebLauncher:
    """
    Safe Website Launcher that restricts browser navigation strictly to
    verified HTTPS web destinations from an explicit allowlist.
    """

    def __init__(self, db: Optional[Any] = None):
        self.db = db
        self.approved_websites = APPROVED_WEBSITES

    def get_approved_websites(self) -> List[Dict[str, str]]:
        """Return the list of approved websites for UI and guidance."""
        return [
            {
                "id": site_id,
                "name": data["display_name"],
                "url": data["url"],
                "description": data["description"]
            }
            for site_id, data in self.approved_websites.items()
        ]

    def is_web_target(self, text: str) -> bool:
        """
        Determine if a candidate target phrase represents a web navigation intent
        rather than a local desktop application or system action.
        """
        clean = text.strip().lower()
        clean = clean.rstrip(".!?,")

        # 1. Matches any approved website alias
        if self.match_website(clean) is not None:
            return True

        # 2. Contains protocol scheme or www
        if re.search(r"^(?:https?://|www\.)", clean):
            return True

        # 3. Contains domain suffix
        if re.search(r"\.(?:com|org|net|io|co|gov|edu|ai|app|dev|site|xyz|info|tv)\b", clean):
            return True

        # 4. Contains IP address
        if re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", clean):
            return True

        # 5. URL shorteners
        if re.search(r"\b(?:bit\.ly|tinyurl\.com|t\.co|goo\.gl|ow\.ly)\b", clean):
            return True

        # 6. Web indicator words or common web domains
        words = set(re.findall(r"[a-z0-9]+", clean))
        if words.intersection(COMMON_WEB_INDICATORS):
            return True
        if any(term in clean for term in ("website", "web page", "site", "webpage", "url", "link")):
            return True

        return False

    def match_website(self, raw_name: str) -> Optional[str]:
        """
        Match a raw user phrase against the approved websites allowlist.
        Strips common filler articles ('the', 'my', 'a', 'website', 'site', 'page').
        Strictly rejects shell metacharacters and requires an exact alias match.
        Returns the matching site_id or None if unapproved.
        """
        clean = raw_name.strip().lower()
        # Strip common trailing punctuation
        clean = clean.rstrip(".!?,")

        # Reject any shell metacharacters or chaining operators
        if any(char in clean for char in (";", "&", "|", ">", "<", "`", "$", "\n", "\\")):
            return None

        # Strip URL trailing slash for alias matching
        if clean.endswith("/"):
            clean = clean[:-1]

        # Strip leading filler articles
        clean = re.sub(r"^(?:the|my|a|an)\s+", "", clean).strip()
        # Strip trailing web filler words
        clean = re.sub(r"\s+(?:website|site|webpage|page|web|portal)$", "", clean).strip()

        # Exact alias match
        for site_id, data in self.approved_websites.items():
            for alias in data["aliases"]:
                alias_clean = alias.rstrip("/")
                if clean == alias_clean or clean == site_id:
                    return site_id

        return None

    def launch_website(self, site_id: str) -> Dict[str, Any]:
        """
        Open an approved website in the user's default browser.
        Guarantees:
        - Only exact pre-approved HTTPS URLs from the hardcoded dictionary are ever opened.
        - User input is NEVER evaluated as a URL or executed as code.
        - Never uses shell=True.
        - Opens in default external browser via webbrowser.open_new_tab().
        """
        if site_id not in self.approved_websites:
            return {
                "success": False,
                "error": f"Security Notice: '{site_id}' is not in the approved website allowlist."
            }

        site_info = self.approved_websites[site_id]
        display_name = site_info["display_name"]
        exact_url = site_info["url"]

        try:
            # Use Python's standard webbrowser module to open in default browser
            opened = webbrowser.open_new_tab(exact_url)

            # Audit log into SQLite database if connected
            if self.db:
                self.db.log_audit("INFO", "WEB_LAUNCH", f"Opened approved website '{display_name}' ({exact_url})")

            logger.info(f"Successfully launched approved website: {display_name} -> {exact_url}")
            return {
                "success": True,
                "site_id": site_id,
                "display_name": display_name,
                "url": exact_url
            }

        except Exception as e:
            err_msg = f"Failed to open {display_name} in default browser: {e}"
            logger.error(err_msg)
            if self.db:
                self.db.log_audit("ERROR", "WEB_LAUNCH_FAIL", err_msg)
            return {"success": False, "error": err_msg}

    def handle_command(self, user_input: str, callsign: str = "Boss") -> Tuple[bool, str]:
        """
        Parse and process natural-language website navigation commands.
        Returns:
            (is_web_command: bool, reply_message: str)
        If the command is not a website navigation attempt, returns (False, "").
        If it is a web navigation attempt:
            - Approved: opens in default browser and returns in-character confirmation.
            - Unapproved, Arbitrary URL, or Malicious: safely rejects and returns protocol explanation.
        """
        clean = user_input.strip()
        lower = clean.lower()

        # 1. Check for web navigation directives:
        # e.g., "go to chatgpt", "take me to github", "visit wikipedia", "navigate to reddit", "browse to google"
        # and shared verbs: "open youtube", "launch google"
        web_regex = r"^(?:edith[,\s]+)?(?:please\s+)?(?:can\s+you\s+)?(?:go\s+to|take\s+me\s+to|visit|navigate\s+to|browse\s+to|open|launch)\b(?:\s+(.+))?$"
        match = re.match(web_regex, lower)

        if not match:
            return False, ""

        raw_target = match.group(1)

        # Case 1: User just said "go to", "visit", "open website", etc. without naming a site
        if not raw_target or not raw_target.strip():
            approved_list = ", ".join(d["display_name"] for d in self.approved_websites.values())
            return True, (
                f"Please specify which approved website you would like me to open, {callsign}. "
                f"Currently authorized: {approved_list}."
            )

        target_cleaned = raw_target.strip().rstrip(".!?,")

        # Exclude non-web intents that use "open" (e.g. memories, tasks, settings, search results)
        if target_cleaned in ("memories", "memory", "my memories", "notes", "my notes", "tasks", "my tasks", "reminders", "settings"):
            return False, ""
        if re.match(r"^(?:result|file|folder|item)\s+\d+\b", target_cleaned):
            return False, ""

        # Check if the target is an approved website
        matched_id = self.match_website(target_cleaned)

        if matched_id:
            # Approved website: Open safely in default browser
            result = self.launch_website(matched_id)
            if result["success"]:
                display_name = result["display_name"]
                confirmations = [
                    f"Opening {display_name} in your default browser, {callsign}.",
                    f"Navigating to {display_name} now, {callsign}.",
                    f"Accessing {display_name}. Secure browser protocol initialized, {callsign}."
                ]
                import random
                return True, random.choice(confirmations)
            else:
                return True, f"Notice: Could not open {result.get('display_name', target_cleaned)}, {callsign}. {result.get('error', '')}"

        # If not an approved website:
        # Check if this command was a web-specific directive ("go to", "visit", "take me to", "navigate to", "browse to")
        # OR if the target is clearly a web domain / URL / website indicator
        verb_match = re.match(r"^(?:edith[,\s]+)?(?:please\s+)?(?:can\s+you\s+)?(go\s+to|take\s+me\s+to|visit|navigate\s+to|browse\s+to)\b", lower)
        is_web_verb = verb_match is not None
        is_web_target_flag = self.is_web_target(target_cleaned)

        if is_web_verb or is_web_target_flag:
            # Unapproved website or arbitrary URL attempt: REJECT SAFELY
            approved_list = ", ".join(d["display_name"] for d in self.approved_websites.values())
            return True, (
                f"Security Protocol Notice: '{target_cleaned}' is not on the approved website allowlist, {callsign}. "
                f"For system safety, I can only navigate to: {approved_list}."
            )

        # If it was "open X" or "launch X" and X is not recognized as a web target,
        # return (False, "") so other handlers (or app launcher) can process it
        return False, ""
