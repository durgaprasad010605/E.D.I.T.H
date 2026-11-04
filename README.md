# E.D.I.T.H. (Even Dead, I'm The Hero)
### Personal Lightweight Desktop AI Assistant // Milestone 4.4: Local Wake Word & Hands-Free Voice Activation

E.D.I.T.H. is an open-source, lightweight personal desktop assistant engineered with a futuristic Stark-tech HUD aesthetic. It runs 100% locally on your machine with zero cloud dependencies, zero subscriptions, and low memory consumption.

---

## What is in Milestone 4.4 (Current Release)

- **Local Offline Wake-Word Detection for "Hey EDITH" (`voice/wake_word.py`)**:
  - **100% Local & Offline**: Detects "Hey EDITH" (and canonical variants like "Edith") without any cloud APIs, third-party subscriptions, or remote calls.
  - **Lightweight Two-Stage Architecture**:
    - **Stage 1 (Energy Gate)**: Near 0.0% CPU usage while the room is quiet or ambient noise is present.
    - **Stage 2 (Local VAD & Keyword Spotter)**: Uses local Silero VAD v6 (`silero_vad_v6.onnx` via ONNX Runtime) and gated Faster-Whisper tiny.en INT8 model spotter. Faster-Whisper is **never** continuously run during silence.
    - **Model Deduplication**: Reuses the already-loaded Faster-Whisper and Piper models in-memory, requiring under 1 MB of additional RAM!
  - **In-Memory Sci-Fi Acknowledgement Chime**:
    - Synthesizes a high-tech two-tone activation earcon in RAM (784 Hz -> 1046.5 Hz) and plays asynchronously via native Windows audio. Zero audio files saved to disk.
  - **Automatic Hands-Free Recording**:
    - Automatically transitions the assistant from `STANDBY` to `WAKE WORD DETECTED` and `LISTENING` upon hearing "Hey EDITH".
    - No manual clicking of the microphone button required.
  - **Local Speech-End Detection (VAD)**:
    - Automatically senses when the user begins speaking their command.
    - Continues recording across short natural pauses between words.
    - Automatically stops recording after **1.5 seconds of continuous silence** (configurable via System Settings).
    - Maximum recording duration safety cutoff (15.0 seconds) prevents runaway recording.
  - **Complete HUD State Management**:
    - Reflects clear real-time states in the Arc Reactor core and input controls:
      - `STANDBY`: Waiting for "Hey EDITH"
      - `WAKE WORD DETECTED`: Activation recognized
      - `LISTENING`: Recording user directive hands-free
      - `PROCESSING`: Transcribing directive and executing
      - `SPEAKING`: EDITH responding aloud via Piper TTS
      - `ERROR`: Audio/mic hardware notice
    - Preserves existing manual microphone button as an instant fallback.
    - Obvious toggle in Header and Settings Modal to disable/enable hands-free listening immediately.
    - Releases hardware microphone completely when disabled or on application shutdown.
    - Pauses listening while EDITH speaks to prevent audio feedback / self-trigger loops.

- **Safe Local File & Folder Search (`core/file_search.py`)**:
  - **Authorized Search Roots**: Dynamic resolution of actual Windows user directories (Desktop, Documents, Downloads, Pictures, Videos, Music) via Windows Registry (`User Shell Folders`), supporting OneDrive redirection without hardcoded paths.
  - **Explicit Project Search**: Project repository (`B:\E.D.I.T.H\`) is searchable only when explicitly requested (e.g., *"Find test files in EDITH"*).
  - **Natural-Language Search Directives**:
    - *"Find my PDF files"*
    - *"Search for resume"*
    - *"Find Project Report"*
    - *"Find images in Downloads"*
    - *"Find Python files"*
    - *"Search for files named budget"*
    - *"Find folders named Projects"*
  - **Clean HUD Results & Pagination**: Displays up to 10 results per page with filename, file type, folder location, and last modified timestamp. Directives *"Show more results"* or *"Next page"* cycle through further results.
  - **Safe Execution & Path Traversal Shield**:
    - **Read-Only**: Never deletes, modifies, renames, moves, uploads, or indexes file contents.
    - **No Automatic Opening**: Discovered files are never opened automatically.
    - **Safe Associated Open**: Explicit command *"Open result [number]"* opens files safely in their default Windows associated viewer via `os.startfile`.
    - **Containing Folder View**: Explicit command *"Open folder [number]"* opens the containing directory in File Explorer.
    - **Binary Execution Blocker**: Direct execution of `.exe`, `.bat`, `.cmd`, `.ps1` from search results is blocked with an explanatory security protocol alert.
    - **Exclusion of System & Hidden Folders**: Automatically skips hidden items (`.*`), Windows system folders (`Windows`, `System32`), `AppData`, application caches, and symbolic links/junctions.

- **Safe Website Launcher (`core/web_launcher.py`)**:
  - **Strict Website Allowlist**: Restricts browser navigation strictly to 8 pre-approved HTTPS destinations:
    1. **Google** — `https://www.google.com/`
    2. **YouTube** — `https://www.youtube.com/`
    3. **ChatGPT** — `https://chatgpt.com/`
    4. **Wikipedia** — `https://www.wikipedia.org/`
    5. **Gmail** — `https://mail.google.com/`
    6. **GitHub** — `https://github.com/`
    7. **Reddit** — `https://www.reddit.com/`
    8. **Stack Overflow** — `https://stackoverflow.com/`
  - **Natural-Language Voice & Text Directives**:
    - *"Open YouTube"*, *"EDITH, please open YouTube"*
    - *"Launch Google"*, *"Search Google"*
    - *"Go to ChatGPT"*, *"Can you go to ChatGPT?"*
    - *"Open Gmail"*, *"Open my email"*
    - *"Take me to GitHub"*
    - *"Visit Wikipedia"*, *"Visit wiki"*
    - *"Open Reddit"*, *"Browse to Reddit"*
    - *"Go to Stack Overflow"*, *"Navigate to Stack Overflow"*
  - **Default Browser Dispatch**: Opens web destinations in the user's default operating system browser via Python's standard `webbrowser` module (`open_new_tab()`). Never opens websites inside embedded PyWebView windows.
  - **Strict Anti-Injection & URL Shield**:
    - Only exact, verified HTTPS URLs from the hardcoded internal allowlist are ever opened.
    - User input is NEVER evaluated as a URL, argument, or shell command.
    - Automatically rejects unknown domains, IP addresses (e.g. `192.168.1.1`), URL shorteners (e.g. `bit.ly`), unapproved websites, and plain HTTP links.
    - Zero credential interaction: E.D.I.T.H. never accesses, stores, or inputs web credentials or automates logins.
    - Audit logging of all web launch events and attempts in local SQLite database.

- **Safe Application Launcher (`core/app_launcher.py`)**:
  - **Strict Application Allowlist**: Only explicitly pre-approved Windows system applications can be launched:
    1. **Notepad** (`notepad.exe`)
    2. **Calculator** (`calc.exe`)
    3. **File Explorer** (`explorer.exe`)
    4. **Paint** (`mspaint.exe`)
    5. **Task Manager** (`taskmgr.exe`)
  - **Natural-Language Voice & Text Directives**:
    - *"Open Notepad"*, *"EDITH, please open notepad"*
    - *"Launch Calculator"*, *"Can you launch the calculator?"*
    - *"Open File Explorer"*, *"Open files"*
    - *"Start Paint"*, *"Start my paint app"*
    - *"Open Task Manager"*, *"Run task manager"*
  - **Zero Arbitrary Execution & Anti-Injection Architecture**:
    - Strictly enforces `shell=False` on all spawned processes.
    - Zero user parameters or shell strings are ever passed to the operating system command line.
    - Strict rejection of all shell metacharacters (`;`, `&`, `|`, `>`, `<`, `` ` ``, `$`, `\n`, `\`, `/`, `-`).
    - Unapproved applications, terminal commands (`cmd`, `powershell`), or arbitrary scripts are refused safely with an informative security protocol notice.
    - Clean process detachment (`DETACHED_PROCESS`) prevents blocking EDITH's thread or loop.
    - Audit logging of all launch events and attempts in local SQLite database.

- **Persistent Personal Memory (Milestone 3)**:
  - Explicit memory storage: *"Remember that my project is called EDITH"*, *"Remember that I prefer dark mode"*.
  - Targeted memory recall: *"What do you remember about my project?"*.
  - Full memory archive review: *"What do you remember?"* / *"Show memories"*.
  - Forget/erase memory: *"Forget that particular note"*, *"Forget [topic]"*.
  - **Zero Credential Logging**: Built-in privacy shield automatically blocks passwords, private cryptographic keys, and financial credentials from storage.
  - **Zero Hallucination Guarantee**: E.D.I.T.H. never pretends to remember notes that are not actually stored.
- **Tactical Task Management (Milestone 3)**:
  - Add tasks via speech or typing: *"Add a task to finish my project documentation"*, *"New task: inspect telemetry (due tomorrow)"*.
  - List pending tasks: *"What are my pending tasks?"* / *"Show tasks"*.
  - List completed tasks: *"Show completed tasks"*.
  - Complete tasks: *"Mark my documentation task as complete"*, *"Finish task [X]"*.
  - Delete tasks: *"Delete task [X]"*.
  - Interactive checkboxes with strikethrough styling in the HUD Tactical Archive.
- **Scheduled Reminders & Live HUD Alerts (Milestone 3)**:
  - Natural time parsing: *"Remind me to run diagnostics in 15 minutes"*, *"Remind me to call Tony at 5:00 PM"*.
  - Non-blocking due reminder polling in the telemetry heartbeat (every 2.5s).
  - Prominent cinematic alert chimes and HUD notification bubbles upon reminder due.
  - Spoken reminder notification aloud via Piper TTS.
  - Duplicate notification shield: reminders are flagged once notified to prevent repeat alerts across application restarts.
- **Tactical Archive Modal (Milestone 3)**:
  - Dedicated HUD modal accessible via the header archive icon `[📚]` or directives.
  - Interactive tabs for `MEMORIES`, `TASKS`, and `REMINDERS`.
  - Filter tasks by `ALL`, `PENDING`, or `COMPLETED`.
  - Search memories in real-time.
  - Inline edit and delete capabilities for all entries.
- **Complete Offline Voice Pipeline (Milestones 2A & 2B)**:
  - **Faster-Whisper (`tiny.en`, INT8, CPU)**: Sub-second offline speech recognition with in-memory audio processing and zero disk footprint.
  - **Piper TTS (`en_US-amy-medium`)**: Natural, cinematic female American-English voice synthesis with background non-blocking audio playback.
  - Mute/unmute toggle in header and settings with persistent storage in SQLite.
- **Futuristic Desktop HUD**: Built with Python and `pywebview` using Windows' native Edge WebView2 engine.
- **Holographic Arc Reactor Visualizer**: 60 FPS animated multi-ring canvas that dynamically reacts when E.D.I.T.H. is idle, listening, transcribing, or speaking.
- **Hardware Telemetry HUD**: Live local monitoring of CPU usage, RAM utilization (used vs available), battery level, disk volume, and system uptime.
- **Safe Local SQLite Repository**: `data/edith.db` with safe migrations, foreign key constraints, and Git exclusion.

---

## Memory Footprint

On a 16 GB RAM PC:
- **Base Backend & Launcher**: ~40 MB
- **Whisper STT (tiny.en int8) Loaded**: ~115 MB
- **Piper TTS (en_US-amy-medium) Loaded**: ~80 MB
- **PyWebView Desktop Window**: ~75 MB
- **Total Concurrent Footprint**: **~270 MB to 310 MB RAM** (Leaves over 98% of your computer free).

---

## Project Structure

```
b:\E.D.I.T.H\
├── core/
│   ├── __init__.py
│   ├── config.py           # Paths, window constants, and system settings
│   ├── app_launcher.py     # Safe application launcher with strict allowlist (Milestone 4.1)
│   ├── web_launcher.py     # Safe website launcher with strict HTTPS allowlist (Milestone 4.2)
│   ├── file_search.py      # Safe local file search with dynamic roots & anti-injection (Milestone 4.3)
│   ├── system_monitor.py   # Live local CPU, RAM, battery telemetry (psutil)
│   └── assistant.py        # PyWebView Python-JS bridge, orchestrator, and voice dispatch
├── brain/
│   ├── __init__.py
│   ├── base.py             # Abstract BaseBrain interface for pluggable AI
│   └── mock_brain.py       # Intelligent in-character rule-based EDITH persona
├── memory/
│   ├── __init__.py
│   └── database.py         # Local SQLite schema & repository
├── voice/                  # Complete Voice Pipeline (STT + TTS)
│   ├── __init__.py
│   ├── engine.py           # Piper TTS background worker engine & deduplicator
│   ├── stt.py              # Faster-Whisper in-memory STT & microphone stream
│   └── models/             # Local voice model files
│       ├── en_US-amy-medium.onnx        (63 MB ONNX Piper neural voice model)
│       ├── en_US-amy-medium.onnx.json   (phoneme config & phonemizer map)
│       ├── MODEL_CARD                   (license and dataset documentation)
│       └── whisper/                     (Cached local Faster-Whisper tiny.en files)
├── ui/
│   ├── index.html          # Futuristic desktop HUD structure with mic & mute controls
│   ├── style.css           # Glassmorphism, cyber neon accents, 60fps animations
│   └── app.js              # Canvas visualizer, mic recording states, bridge hooks
├── data/                   # Stores edith.db and audio cache (gitignored)
├── main.py                 # Main application desktop entrypoint
├── run.bat                 # 1-click Windows launcher
├── test_stt.py             # Standalone STT and end-to-end voice loop test
├── test_voice.py           # Standalone Piper TTS voice test
├── test_backend.py         # Automated backend, TTS & STT test suite
├── test_window.py          # Automated GUI smoke test
├── .gitignore              # Future-proof repository security configuration
└── requirements.txt        # pywebview, psutil, piper-tts, faster-whisper, sounddevice
```

---

## Quick Start on Windows

### 1. Requirements
- Windows 10 or 11 (with Microsoft Edge WebView2, built-in by default).
- Python 3.10+ installed and added to `PATH`.
- A microphone (built-in or USB headset).

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

## How to Test Voice Input & Output (Milestone 2B)

### Step 1: Run the Standalone Speech Recognition & Dialogue Test
Run:
```bash
python test_stt.py
```
This test automatically:
1. Detects your physical microphone input device.
2. Initializes Faster-Whisper `tiny.en` with INT8 CPU quantization.
3. Tests transcription latency and accuracy on benchmark speech.
4. Verifies in-memory audio recording stream start/stop.
5. Feeds recognized speech through the assistant pipeline and plays E.D.I.T.H.'s response aloud via Piper TTS.

### Step 2: Test Spoken Interaction Inside the Desktop HUD
1. Launch E.D.I.T.H. via `run.bat` or `python main.py`.
2. Locate the **Microphone Button** next to the chat text box.
3. **Click the mic button**:
   - The button pulses **red** (`LISTENING`).
   - The central arc reactor shows `LISTENING...`.
4. **Speak a command into your microphone**:
   - E.g., *"Status report"*, *"Who are you?"*, or *"What time is it?"*.
5. **Click the mic button again to stop**:
   - The button shows a rotating cyan border (`TRANSCRIBING`).
   - Faster-Whisper transcribes your speech in memory.
   - The recognized text automatically populates the chat input and transmits.
   - E.D.I.T.H. responds in the console and **speaks her response aloud** through your speakers/headphones!

### Step 3: Test Safe Application Launching (Milestone 4.1)
1. Launch E.D.I.T.H. via `run.bat` or `python main.py`.
2. In the chat text box or via voice microphone, try:
   - `"Open Notepad"` or `"EDITH, please open notepad"`
   - `"Launch Calculator"` or `"Can you launch the calculator?"`
   - `"Open File Explorer"`
   - `"Start Paint"`
   - `"Open Task Manager"`
3. Notice that:
   - The application opens immediately on Windows in a detached process.
   - EDITH speaks a confirmation aloud through Piper TTS: *"Opening Notepad, Boss. Process initialized."*
   - An audit log entry is saved in SQLite database.
4. Try an unapproved application or command injection:
   - `"Open cmd"`
   - `"Launch powershell"`
   - `"Open chrome"`
   - `"Launch calc && whoami"`
5. Notice that EDITH refuses safely:
   - *"Security Protocol Notice: 'cmd' is not on the approved application allowlist, Boss. For system safety, I can currently only launch: Notepad, Calculator, File Explorer, Paint, Task Manager."*
   - No terminal or subprocess is ever spawned.

### Step 4: Test Safe Website Launching (Milestone 4.2)
1. Launch E.D.I.T.H. via `run.bat` or `python main.py`.
2. In the chat text box or via voice microphone, try:
   - `"Open YouTube"` or `"EDITH, please open YouTube"`
   - `"Launch Google"`
   - `"Go to ChatGPT"`
   - `"Open Gmail"` or `"Open my email"`
   - `"Take me to GitHub"`
   - `"Visit Wikipedia"`
   - `"Open Reddit"`
   - `"Go to Stack Overflow"`
3. Notice that:
   - The approved HTTPS website opens in your default system browser in a new tab.
   - EDITH speaks a confirmation aloud through Piper TTS: *"Opening YouTube in your default browser, Boss."*
   - An audit log entry is saved in SQLite database.
4. Try an unapproved website, arbitrary URL, or command injection:
   - `"Open Facebook"`
   - `"Go to Twitter"`
   - `"Open https://malicious.site"`
   - `"Go to http://192.168.1.1"`
   - `"Go to YouTube && whoami"`
5. Notice that EDITH refuses safely:
   - *"Security Protocol Notice: 'facebook' is not on the approved website allowlist, Boss. For system safety, I can only navigate to: Google, YouTube, ChatGPT, Wikipedia, Gmail, GitHub, Reddit, Stack Overflow."*
   - The browser is never opened for unapproved targets.

### Step 5: Test Safe Local File Search (Milestone 4.3)
1. Launch E.D.I.T.H. via `run.bat` or `python main.py`.
2. In the chat text box or via voice microphone, try:
   - `"Find my PDF files"`
   - `"Search for resume"`
   - `"Find images in Downloads"`
   - `"Find Python files"`
   - `"Search for files named budget"`
   - `"Find folders named Projects"`
   - `"Find test files in EDITH"`
3. Notice that:
   - Up to 10 matching files or folders appear in the chat HUD with filename, type, location, and modified date.
   - Files are **not** opened automatically.
4. Try pagination:
   - Type or speak: `"Show more results"` or `"Next page"` to view the next 10 items.
5. Safely open a result or its containing folder:
   - Type or speak: `"Open result 1"` to launch the file in its default Windows associated program (e.g. Acrobat/Photos/Excel).
   - Type or speak: `"Open folder 1"` to reveal the file in File Explorer.
6. Verify safety protections:
   - Searching for an executable (e.g. `installer.exe`) and requesting `"Open result [N]"` is blocked safely:
     *"Security Protocol Notice: Direct execution of '.exe' executable or script files is blocked..."*
   - Hidden folders, Windows system directories, and `AppData` are excluded from search results.

### Step 6: Test Hands-Free Wake-Word & Voice Activation (Milestone 4.4)
1. Launch E.D.I.T.H. via `run.bat` or `python main.py`.
2. Notice the top header indicates: `WAKE WORD: ACTIVE` and the central Arc Reactor displays `STANDBY // WAITING FOR 'HEY EDITH'`.
3. Say clearly into your microphone:
   - **"Hey EDITH"**
4. Observe the automatic activation:
   - A crisp futuristic two-tone chime sounds immediately.
   - The Arc Reactor transitions to **`WAKE WORD DETECTED`**, then pulses red with **`LISTENING // RECORDING DIRECTIVE`**.
   - No mouse clicks or button presses are needed!
5. Speak your command:
   - *"What time is it?"*
   - *"Open Calculator"*
   - *"Open YouTube"*
   - *"Status report"*
   - *"Search for resume in documents"*
6. Stop speaking:
   - Notice that after ~1.5 seconds of silence, E.D.I.T.H. automatically detects the end of your speech.
   - The Arc Reactor transitions to **`PROCESSING // FASTER-WHISPER INT8`**.
   - Your command is executed (e.g. Calculator launches, status report is generated).
   - The Arc Reactor transitions to **`SPEAKING // PIPER NEURAL TTS`** as EDITH speaks her response aloud.
   - Once EDITH finishes speaking, the system smoothly returns to **`STANDBY`** awaiting your next directive!
7. Test the manual fallback and disable toggles:
   - Click the microphone button in the input bar at any time to record manually.
   - Click the hands-free icon button in the header or the toggle switch in Settings to disable wake-word detection immediately (hardware microphone is immediately released).

### Step 7: Run All Verification Suites
- **Milestone 4.4 Hands-Free & Wake-Word Suite**:
  ```bash
  python test_wakeword.py
  ```
- **Milestone 4.4 RAM & CPU Profiling Benchmark**:
  ```bash
  python benchmark_resources.py
  ```
- **Full Backend, Voice, Memory, App, Web & File Search Suite**:
  ```bash
  python test_backend.py
  ```
- **STT & Dialogue Loop Test**:
  ```bash
  python test_stt.py
  ```
- **TTS Standalone Test**:
  ```bash
  python test_voice.py
  ```
- **GUI Window Smoke Test**:
  ```bash
  python test_window.py
  ```

---

## Privacy & Security Guarantee

1. **Zero Cloud Telemetry**: Microphone audio is captured directly in memory and processed locally by Faster-Whisper.
2. **Zero Permanent Audio Files**: Microphone buffers are discarded from memory immediately after transcription. No WAV files of your voice are saved on your computer.
3. **Git Protection**: All runtime data, database caches, and downloaded model weights are excluded by `.gitignore`.
