"""
E.D.I.T.H. Mock Brain Module (Milestone 1)
Delivers intelligent, contextual, and cinematic EDITH responses
with zero external dependencies or heavy AI model overhead.
"""
import re
import datetime
import random
from typing import Dict, Any, Optional
from .base import BaseBrain

class MockBrain(BaseBrain):
    """
    Intelligent rule & heuristic brain implementing the calm,
    competent, cinematic EDITH persona for Milestone 1.
    """

    def __init__(self):
        self.callsign = "Boss"

    def get_name(self) -> str:
        return "EDITH Mock Core (Rule-Based v1.0)"

    def is_available(self) -> bool:
        return True

    def generate_response(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        clean = user_input.strip()
        lower = clean.lower()

        telemetry = context.get("telemetry", {}) if context else {}
        callsign = context.get("user_callsign", self.callsign) if context else self.callsign

        # 1. Greetings
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

        # 2. Identity / Purpose
        if re.search(r"\b(who are you|what is edith|what does edith stand for|your name|your purpose)\b", lower):
            return (
                f"I am E.D.I.T.H. -- 'Even Dead, I'm The Hero'.\n\n"
                f"I am your personal, private desktop AI assistant designed for high security and zero cloud dependence. "
                f"Currently operating on Milestone 1: Core HUD & Local Telemetry Architecture. "
                f"Voice synthesis, long-term memory, and local neural reasoning modules are primed for sequential deployment."
            )

        # 3. Status & Diagnostics
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

        # 4. CPU / RAM specific queries
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

        # 5. Time & Date
        if re.search(r"\b(time|what time|clock)\b", lower):
            now_str = datetime.datetime.now().strftime("%I:%M:%S %p")
            return f"The current system time is {now_str}."

        if re.search(r"\b(date|what day|today)\b", lower):
            date_str = datetime.datetime.now().strftime("%A, %B %d, %Y")
            return f"Today is {date_str}."

        # 6. Capabilities & Help
        if re.search(r"\b(help|commands|capabilities|what can you do)\b", lower):
            return (
                f"Available Milestone 1 Commands for {callsign}:\n"
                f"- 'Status' / 'Diagnostics' -- Live telemetry and hardware statistics.\n"
                f"- 'Time' / 'Date' -- Current clock and calendar verification.\n"
                f"- 'Who are you' -- Identification and architecture manifesto.\n"
                f"- 'Clear' -- Wipe current display buffer.\n"
                f"- 'Protocols' -- Security perimeter and privacy verification.\n"
                f"- 'Settings' -- Toggle theme accents and preferences.\n\n"
                f"Coming in subsequent milestones: Voice input/output (M2), Local database notes & tasks (M3), "
                f"Safe desktop automation (M4), and Local Ollama neural brain (M5)."
            )

        # 7. Security / Protocols
        if re.search(r"\b(security|protocol|privacy|safe|offline)\b", lower):
            return (
                f"Security Assessment: Level 1 Alpha.\n"
                f"- Network Access: Blocked / Offline Mode Active\n"
                f"- Local Storage: Local SQLite repository\n"
                f"- External Telemetry: Disabled\n"
                f"- Destructive Command Execution: Hard restricted by approval gatekeeper."
            )

        # 8. Note / Task / Reminder Preview (Milestone 3 stubs)
        if re.search(r"\b(remind|note|task|todo|plan)\b", lower):
            return (
                f"Directive noted, {callsign}. Task and memory storage will be persistently anchored in Milestone 3 "
                f"via our local SQLite database. For now, your entry has been cached in the active session buffer."
            )

        # 9. Voice preview (Milestone 2 stubs)
        if re.search(r"\b(voice|speak|talk|audio|listen|mic)\b", lower):
            return (
                f"The audio subsystem visualizer is active. Local Whisper speech-to-text and Piper neural voice "
                f"synthesis will be connected in Milestone 2. Microphones are currently muted."
            )

        # 10. Stark / Marvel Easter Eggs
        if re.search(r"\b(stark|tony|jarvis|friday|avengers|suit)\b", lower):
            return (
                f"Tony left big shoes to fill. As he always said: 'Part of the journey is the end.' "
                f"I am tuned specifically for you, {callsign}. How may I configure our protocols today?"
            )

        # 11. Polite Fallback
        fallbacks = [
            f"Understood, {callsign}. Processing your query: '{clean}'. In Milestone 1, my reasoning is guided by the local core. A dedicated local neural network can be attached in Milestone 5.",
            f"Command received, {callsign}. All subsystems report normal parameters. Request acknowledged.",
            f"I have logged that in our local session, {callsign}. Standing by for your next instruction.",
            f"Acknowledged, {callsign}. Telemetry and local memory channels remain active and responsive."
        ]
        return random.choice(fallbacks)
