# E.D.I.T.H. (Even Dead, I'm The Hero)
### Personal Lightweight Desktop AI Assistant // Milestone 1

E.D.I.T.H. is an open-source, lightweight personal desktop assistant engineered with a futuristic Stark-tech HUD aesthetic. It runs 100% locally on your machine with zero cloud dependencies, zero subscriptions, and low memory consumption.

---

## What is in Milestone 1

- **Futuristic Desktop HUD**: Built with Python and `pywebview` using Windows' native Edge WebView2 engine.
- **Holographic Arc Reactor Visualizer**: 60 FPS animated multi-ring canvas that dynamically reacts when E.D.I.T.H. is idle, analyzing, or replying.
- **Hardware Telemetry HUD**: Live local monitoring of CPU usage, RAM utilization (used vs available), battery level, disk volume, and system uptime.
- **Communications Console**: Real-time two-way dialogue panel with message history and quick directive chips.
- **Intelligent Local Mock Brain**: Instant in-character persona responses for greetings, status diagnostics, time/date, security protocols, and help commands with zero model overhead.
- **Persistent Local Memory**: Local SQLite database (`data/edith.db`) storing conversation history, audit logs, and user preferences.
- **Synthesized Audio Feedback**: Built-in Web Audio API sound effects (sci-fi startup, send, and receive chimes) without downloading external audio assets.
- **Settings Panel**: Custom operator callsign (e.g., "Boss", "Tony"), theme selector (*Stark Cyan*, *Mark 85 Amber*, *Stealth Violet*), and sound toggle.
- **Microphone Placeholder**: Ready for Milestone 2 voice pipeline integration.

---

## Memory Footprint (Milestone 1)

On a 16 GB RAM PC:
- **Python Backend**: ~35 MB
- **PyWebView Desktop Window**: ~75 MB
- **Total Footprint**: **~110 MB to 150 MB RAM** (Leaves over 98% of your computer free).

---

## Project Structure

```
b:\E.D.I.T.H\
├── core/
│   ├── __init__.py
│   ├── config.py           # Paths, window constants, and default settings
│   ├── system_monitor.py   # Live local CPU, RAM, battery telemetry (psutil)
│   └── assistant.py        # PyWebView Python-JS bridge and orchestrator
├── brain/
│   ├── __init__.py
│   ├── base.py             # Abstract BaseBrain interface for pluggable AI
│   └── mock_brain.py       # Intelligent in-character rule-based EDITH persona
├── memory/
│   ├── __init__.py
│   └── database.py         # Local SQLite schema & repository
├── voice/                  # Stubs prepared for Milestone 2 (STT & TTS)
│   ├── __init__.py
│   └── engine.py           # Voice engine interface
├── ui/
│   ├── index.html          # Futuristic desktop HUD structure
│   ├── style.css           # Glassmorphism, cyber neon accents, 60fps animations
│   └── app.js              # Canvas visualizer, telemetry polling, bridge client
├── data/                   # Created automatically: stores edith.db
├── main.py                 # Main application desktop entrypoint
├── run.bat                 # 1-click Windows launcher
├── test_backend.py         # Automated backend test suite
├── test_window.py          # Automated GUI smoke test
└── requirements.txt        # pywebview, psutil
```

---

## Quick Start on Windows

### 1. Requirements
- Windows 10 or 11 (with Microsoft Edge WebView2, built-in by default).
- Python 3.10+ installed and added to `PATH`.

### 2. Installation
Open PowerShell or Command Prompt in the project folder and run:
```bash
cd b:\E.D.I.T.H
pip install -r requirements.txt
```

### 3. Launching E.D.I.T.H.
Double-click `run.bat` or run:
```bash
python main.py
```

---

## How to Test Milestone 1

1. **Verify Startup**:
   - The desktop window opens with dark obsidian glassmorphism and cyan lighting.
   - The central arc reactor ring pulses and rotates smoothly.
   - Live CPU, RAM, and Battery percentages populate in the telemetry grid.

2. **Test Directives (Type or click quick chips)**:
   - Type `Hello EDITH` → E.D.I.T.H. greets you with time-of-day awareness.
   - Type `Status report` → Returns live CPU %, RAM footprint, uptime, and security level.
   - Type `Who are you?` → Explains her identity and architecture manifesto.
   - Type `What time is it?` → Returns accurate local system time.
   - Type `Clear` → Wipes the conversation buffer.

3. **Test Settings**:
   - Click the gear icon (`⚙`) in the top right.
   - Change your callsign (e.g., from `Boss` to your name).
   - Switch themes (*Stark Cyan*, *Mark 85 Amber*, or *Stealth Violet*).
   - Click **Apply Configuration**; changes take effect immediately and are saved to `data/edith.db`.

4. **Run Automated Test Suites**:
   - Backend logic test:
     ```bash
     python test_backend.py
     ```
   - GUI window smoke test:
     ```bash
     python test_window.py
     ```

---

## What's Next in Milestone 2 (Voice Pipeline)

Once you approve Milestone 1, Milestone 2 will introduce:
1. **Local Speech-to-Text (STT)**: Using `faster-whisper` (`base.en`) for offline voice input.
2. **Cinematic Voice Output (TTS)**: Piper offline neural voice synthesis + `edge-tts` fallback for a calm, cinematic female voice.
3. **Sound-reactive Waveform**: The central visualizer will pulse to the exact frequencies of your voice and E.D.I.T.H.'s speech.
