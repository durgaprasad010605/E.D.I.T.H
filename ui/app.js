/* ============================================================
   E.D.I.T.H. HUD Controller & Bridge Interface
   Milestone 1: Desktop Shell, Holographic Canvas & Telemetry
   ============================================================ */

(() => {
  // Application State
  const state = {
    initialized: false,
    bridgeReady: false,
    soundEnabled: true,
    voiceMuted: false,
    isRecording: false,
    isStartingMic: false,
    isTranscribing: false,
    archiveOpen: false,
    activeTaskFilter: 'all',
    userCallsign: "Boss",
    currentTheme: "cyan",
    telemetryTimer: null,
    isProcessing: false,
    audioContext: null,
    wakeWordEnabled: true,
    hudState: "STANDBY"
  };

  // DOM Elements
  const elements = {
    // Header
    headerCpu: document.getElementById('header-cpu-val'),
    headerRam: document.getElementById('header-ram-val'),
    statusUptime: document.getElementById('status-uptime'),
    statusProtocol: document.getElementById('status-protocol'),
    badgeWakeWord: document.getElementById('status-wakeword-badge'),
    badgeWakeWordText: document.getElementById('badge-wakeword-text'),
    btnWakeWordToggle: document.getElementById('btn-wakeword-toggle'),
    btnMuteToggle: document.getElementById('btn-mute-toggle'),
    iconUnmuted: document.getElementById('icon-unmuted'),
    iconMuted: document.getElementById('icon-muted'),
    btnClearChat: document.getElementById('btn-clear-chat'),
    btnOpenSettings: document.getElementById('btn-open-settings'),

    // Visualizer & Core
    canvas: document.getElementById('visualizer-canvas'),
    coreStatusLabel: document.getElementById('core-status-label'),
    coreEngineLabel: document.getElementById('core-engine-label'),

    // Telemetry Cards
    cardCpuVal: document.getElementById('card-cpu-val'),
    meterCpuFill: document.getElementById('meter-cpu-fill'),
    cardRamVal: document.getElementById('card-ram-val'),
    meterRamFill: document.getElementById('meter-ram-fill'),
    cardBatteryVal: document.getElementById('card-battery-val'),
    meterBatteryFill: document.getElementById('meter-battery-fill'),
    cardDiskVal: document.getElementById('card-disk-val'),
    meterDiskFill: document.getElementById('meter-disk-fill'),

    // Chat
    messagesContainer: document.getElementById('messages-container'),
    chatForm: document.getElementById('chat-form'),
    userInput: document.getElementById('user-input'),
    btnSend: document.getElementById('btn-send'),
    btnMic: document.getElementById('btn-mic'),

    // Settings Modal
    settingsModal: document.getElementById('settings-modal'),
    btnCloseSettings: document.getElementById('btn-close-settings'),
    btnSaveSettings: document.getElementById('btn-save-settings'),
    btnTestVoice: document.getElementById('btn-test-voice'),
    btnModalMuteToggle: document.getElementById('btn-modal-mute-toggle'),
    modalVoiceStatus: document.getElementById('modal-voice-status'),
    settingCallsign: document.getElementById('setting-callsign'),
    settingSoundFx: document.getElementById('setting-sound-fx'),
    settingWakeWord: document.getElementById('setting-wake-word'),
    settingSilenceTimeout: document.getElementById('setting-silence-timeout'),
    themeChoices: document.querySelectorAll('.theme-choice'),
    chipButtons: document.querySelectorAll('.chip-btn'),

    // Tactical Archive Modal (Milestone 3)
    btnOpenArchive: document.getElementById('btn-open-archive'),
    archiveModal: document.getElementById('archive-modal'),
    btnCloseArchive: document.getElementById('btn-close-archive'),
    archiveTabBtns: document.querySelectorAll('.archive-tab-btn'),
    archiveTabPanes: document.querySelectorAll('.archive-tab-pane'),
    countMemories: document.getElementById('count-memories'),
    countTasks: document.getElementById('count-tasks'),
    countReminders: document.getElementById('count-reminders'),
    inputNewMemory: document.getElementById('input-new-memory'),
    btnAddMemory: document.getElementById('btn-add-memory'),
    searchMemories: document.getElementById('search-memories'),
    memoriesList: document.getElementById('memories-list'),
    inputNewTask: document.getElementById('input-new-task'),
    inputTaskDue: document.getElementById('input-task-due'),
    btnAddTask: document.getElementById('btn-add-task'),
    taskFilterBtns: document.querySelectorAll('.task-filter-btn'),
    tasksList: document.getElementById('tasks-list'),
    inputNewReminder: document.getElementById('input-new-reminder'),
    inputReminderTime: document.getElementById('input-reminder-time'),
    btnAddReminder: document.getElementById('btn-add-reminder'),
    remindersList: document.getElementById('reminders-list')
  };

  // ============================================================
  // WEB AUDIO SYNTHESIZER (Pure JS Sci-Fi Audio Feedback)
  // ============================================================
  function playTone(freq, duration = 0.1, type = 'sine') {
    if (!state.soundEnabled) return;
    try {
      if (!state.audioContext) {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (AudioCtx) state.audioContext = new AudioCtx();
      }
      if (!state.audioContext) return;
      if (state.audioContext.state === 'suspended') {
        state.audioContext.resume();
      }

      const osc = state.audioContext.createOscillator();
      const gain = state.audioContext.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(freq, state.audioContext.currentTime);

      gain.gain.setValueAtTime(0.04, state.audioContext.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, state.audioContext.currentTime + duration);

      osc.connect(gain);
      gain.connect(state.audioContext.destination);

      osc.start();
      osc.stop(state.audioContext.currentTime + duration);
    } catch (e) {
      // Audio context might be restricted before interaction
    }
  }

  function playSoundChime(action) {
    if (action === 'send') {
      playTone(580, 0.08);
      setTimeout(() => playTone(880, 0.12), 80);
    } else if (action === 'receive') {
      playTone(880, 0.08);
      setTimeout(() => playTone(660, 0.14), 70);
    } else if (action === 'click') {
      playTone(1200, 0.04);
    } else if (action === 'startup') {
      playTone(440, 0.1);
      setTimeout(() => playTone(660, 0.12), 100);
      setTimeout(() => playTone(880, 0.2), 220);
    } else if (action === 'alert') {
      playTone(880, 0.1);
      setTimeout(() => playTone(1100, 0.12), 90);
      setTimeout(() => playTone(880, 0.2), 220);
    }
  }

  // ============================================================
  // HOLOGRAPHIC 60FPS CANVAS VISUALIZER
  // ============================================================
  let canvasCtx = null;
  let animFrameId = null;
  let wavePhase = 0;
  let waveIntensity = 1.0;

  function initVisualizer() {
    if (!elements.canvas) return;
    canvasCtx = elements.canvas.getContext('2d');
    animateVisualizer();
  }

  function animateVisualizer() {
    if (!canvasCtx) return;
    const width = elements.canvas.width;
    const height = elements.canvas.height;
    const centerX = width / 2;
    const centerY = height / 2;

    canvasCtx.clearRect(0, 0, width, height);

    // Accent color from active theme
    const isAmber = document.body.classList.contains('theme-amber');
    const isStealth = document.body.classList.contains('theme-stealth');
    const strokeColor = isAmber ? 'rgba(255, 170, 0, 0.7)' : (isStealth ? 'rgba(192, 132, 252, 0.7)' : 'rgba(0, 240, 255, 0.7)');
    const glowColor = isAmber ? '#ffaa00' : (isStealth ? '#c084fc' : '#00f0ff');

    // Smooth return to idle intensity
    if (!state.isProcessing && waveIntensity > 1.0) {
      waveIntensity -= 0.03;
    }

    // Outer Arc Wave
    const numPoints = 64;
    const baseRadius = 125;

    canvasCtx.save();
    canvasCtx.beginPath();
    canvasCtx.strokeStyle = strokeColor;
    canvasCtx.lineWidth = 1.5;
    canvasCtx.shadowBlur = 8;
    canvasCtx.shadowColor = glowColor;

    for (let i = 0; i <= numPoints; i++) {
      const angle = (i / numPoints) * Math.PI * 2;
      const freqOffset = Math.sin(angle * 6 + wavePhase) * (4 * waveIntensity);
      const microJitter = Math.cos(angle * 12 - wavePhase * 1.5) * (2 * waveIntensity);
      const r = baseRadius + freqOffset + microJitter;
      const x = centerX + Math.cos(angle) * r;
      const y = centerY + Math.sin(angle) * r;

      if (i === 0) canvasCtx.moveTo(x, y);
      else canvasCtx.lineTo(x, y);
    }
    canvasCtx.closePath();
    canvasCtx.stroke();
    canvasCtx.restore();

    // Orbital Spark Particles
    const numParticles = 8;
    for (let j = 0; j < numParticles; j++) {
      const pAngle = (j / numParticles) * Math.PI * 2 + (wavePhase * 0.4);
      const pR = baseRadius - 15 + Math.sin(wavePhase * 2 + j) * 8;
      const px = centerX + Math.cos(pAngle) * pR;
      const py = centerY + Math.sin(pAngle) * pR;

      canvasCtx.beginPath();
      canvasCtx.arc(px, py, 1.8, 0, Math.PI * 2);
      canvasCtx.fillStyle = glowColor;
      canvasCtx.shadowBlur = 6;
      canvasCtx.shadowColor = glowColor;
      canvasCtx.fill();
    }

    wavePhase += state.isProcessing ? 0.08 : 0.025;
    animFrameId = requestAnimationFrame(animateVisualizer);
  }

  function setCoreState(status, engine = "LOCAL MOCK v1.0") {
    if (elements.coreStatusLabel) elements.coreStatusLabel.textContent = status;
    if (elements.coreEngineLabel) elements.coreEngineLabel.textContent = engine;

    if (status === "ANALYZING" || status === "PROCESSING" || status === "WAKE WORD DETECTED") {
      state.isProcessing = true;
      waveIntensity = 2.8;
    } else if (status === "LISTENING") {
      state.isProcessing = true;
      waveIntensity = 3.6;
    } else if (status === "SPEAKING") {
      state.isProcessing = true;
      waveIntensity = 2.4;
    } else {
      state.isProcessing = false;
      waveIntensity = 1.0;
    }
  }

  // Visual state controller for Milestone 4.4 HUD states
  function applyHudState(stateName, details = "") {
    state.hudState = stateName;

    if (stateName === "STANDBY") {
      const sub = state.wakeWordEnabled ? "WAITING FOR 'HEY EDITH'" : "LOCAL MOCK v4.4";
      setCoreState("STANDBY", sub);
      if (elements.btnMic && !state.isRecording) {
        elements.btnMic.classList.remove('listening', 'processing', 'recognized', 'error');
        elements.btnMic.title = "Voice Input: Click to Speak / Click to Stop";
      }
    } else if (stateName === "WAKE WORD DETECTED") {
      setCoreState("WAKE WORD DETECTED", "HEY EDITH RECOGNIZED");
      if (elements.btnMic) {
        elements.btnMic.classList.remove('listening', 'processing', 'error');
        elements.btnMic.classList.add('recognized');
      }
    } else if (stateName === "LISTENING") {
      setCoreState("LISTENING", "RECORDING DIRECTIVE");
      if (elements.btnMic) {
        elements.btnMic.classList.remove('processing', 'recognized', 'error');
        elements.btnMic.classList.add('listening');
        elements.btnMic.title = "Listening hands-free... Speak your directive";
      }
    } else if (stateName === "PROCESSING") {
      setCoreState("PROCESSING", "FASTER-WHISPER INT8");
      if (elements.btnMic) {
        elements.btnMic.classList.remove('listening', 'recognized', 'error');
        elements.btnMic.classList.add('processing');
        elements.btnMic.title = "Transcribing & executing...";
      }
    } else if (stateName === "SPEAKING") {
      setCoreState("SPEAKING", "PIPER NEURAL TTS");
      if (elements.btnMic) {
        elements.btnMic.classList.remove('listening', 'processing', 'error');
        elements.btnMic.classList.add('recognized');
      }
    } else if (stateName === "ERROR") {
      setCoreState("ERROR", details || "AUDIO SUBSYSTEM ERROR");
      if (elements.btnMic) {
        elements.btnMic.classList.remove('listening', 'processing', 'recognized');
        elements.btnMic.classList.add('error');
      }
    }
  }

  // Global hooks called from Python via window.evaluate_js
  window.onEdithStateChange = (stateName, details = "") => {
    applyHudState(stateName, details);
  };

  window.onHandsFreeInteraction = (userPrompt, edithReplyData) => {
    playSoundChime('receive');
    appendMessage('USER', userPrompt);
    if (edithReplyData && edithReplyData.reply) {
      appendMessage('EDITH', edithReplyData.reply, edithReplyData.timestamp);
    }
    loadArchiveCounts();
    if (state.archiveOpen) loadArchiveData();
  };

  function updateWakeWordUI(enabled) {
    state.wakeWordEnabled = enabled;
    if (elements.btnWakeWordToggle) {
      elements.btnWakeWordToggle.classList.toggle('active', enabled);
      elements.btnWakeWordToggle.title = enabled
        ? "Hands-Free Wake Word ('Hey EDITH'): Active"
        : "Hands-Free Wake Word ('Hey EDITH'): Inactive (Click to Enable)";
    }
    if (elements.badgeWakeWord) {
      elements.badgeWakeWord.style.borderColor = enabled ? "var(--accent-cyan)" : "var(--border-dim)";
      elements.badgeWakeWord.style.color = enabled ? "var(--accent-cyan)" : "var(--text-muted)";
      const dot = elements.badgeWakeWord.querySelector('.badge-dot');
      if (dot) dot.style.background = enabled ? "var(--accent-cyan)" : "var(--text-muted)";
    }
    if (elements.badgeWakeWordText) {
      elements.badgeWakeWordText.textContent = enabled ? "WAKE WORD: ACTIVE" : "WAKE WORD: OFF";
    }
    if (elements.settingWakeWord) {
      elements.settingWakeWord.checked = enabled;
    }
    if (state.hudState === "STANDBY") {
      setCoreState("STANDBY", enabled ? "WAITING FOR 'HEY EDITH'" : "LOCAL MOCK v4.4");
    }
  }
  }

  // ============================================================
  // PYWEBVIEW NATIVE BRIDGE WRAPPER
  // ============================================================
  const Bridge = {
    isAvailable: () => typeof window.pywebview !== 'undefined' && typeof window.pywebview.api !== 'undefined',

    async getSystemInfo() {
      if (this.isAvailable()) return await window.pywebview.api.get_system_info();
      return {
        app_name: "E.D.I.T.H.",
        version: "1.0.0-M1",
        brain_engine: "EDITH Mock Core (Offline)",
        mode: "LOCAL_BROWSER_PREVIEW"
      };
    },

    async getTelemetry() {
      if (this.isAvailable()) return await window.pywebview.api.get_telemetry();
      // Browser preview simulated telemetry
      return {
        cpu_percent: Math.floor(6 + Math.random() * 8),
        ram_percent: 28,
        ram_used_gb: 4.4,
        ram_total_gb: 16.0,
        ram_available_gb: 11.6,
        battery_percent: 100,
        battery_status: "A/C Line Powered",
        disk_percent: 34,
        disk_free_gb: 340.5,
        uptime: "00:08:42",
        status: "NOMINAL",
        security_protocol: "LOCALHOST ONLY"
      };
    },

    async getHistory() {
      if (this.isAvailable()) return await window.pywebview.api.get_history();
      return [];
    },

    async clearHistory() {
      if (this.isAvailable()) return await window.pywebview.api.clear_history();
      return { success: true };
    },

    async sendMessage(text) {
      if (this.isAvailable()) return await window.pywebview.api.send_message(text);
      // In-browser mock fallback if opened directly without PyWebView
      return {
        reply: `Standing by, ${state.userCallsign}. Message '${text}' processed by browser sandbox.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        sender: "EDITH"
      };
    },

    async getSettings() {
      if (this.isAvailable()) return await window.pywebview.api.get_settings();
      return {
        theme: state.currentTheme,
        user_callsign: state.userCallsign,
        sound_effects: state.soundEnabled,
        voice_muted: state.voiceMuted
      };
    },

    async saveSetting(key, value) {
      if (this.isAvailable()) return await window.pywebview.api.save_setting(key, value);
      return { success: true };
    },

    async toggleMute() {
      if (this.isAvailable()) {
        const res = await window.pywebview.api.toggle_mute();
        return res ? res.is_muted : !state.voiceMuted;
      }
      return !state.voiceMuted;
    },

    async testVoice(phrase = null) {
      if (this.isAvailable()) return await window.pywebview.api.test_voice(phrase);
      return { status: "testing" };
    },

    async stopSpeech() {
      if (this.isAvailable()) return await window.pywebview.api.stop_speech();
      return { stopped: true };
    },

    async startMic() {
      if (this.isAvailable()) return await window.pywebview.api.start_mic();
      return { status: "listening" };
    },

    async stopMic() {
      if (this.isAvailable()) return await window.pywebview.api.stop_mic();
      return { status: "recognized", text: "Voice simulation directive." };
    },

    async cancelMic() {
      if (this.isAvailable()) return await window.pywebview.api.cancel_mic();
      return { status: "cancelled" };
    },

    async getSttStatus() {
      if (this.isAvailable()) return await window.pywebview.api.get_stt_status();
      return { mic_available: true, engine: "Faster-Whisper (Offline)" };
    },

    // Milestone 4.4: Wake-Word & Hands-Free Activation Bridge
    async getHudStatus() {
      if (this.isAvailable()) return await window.pywebview.api.get_hud_status();
      return { hud_state: state.hudState, wake_word_enabled: state.wakeWordEnabled };
    },

    async toggleWakeWord() {
      if (this.isAvailable()) return await window.pywebview.api.toggle_wake_word();
      return { enabled: !state.wakeWordEnabled };
    },

    async setWakeWordEnabled(enabled) {
      if (this.isAvailable()) return await window.pywebview.api.set_wake_word_enabled(enabled);
      return { enabled };
    },

    async setVadSilenceDuration(durationSec) {
      if (this.isAvailable()) return await window.pywebview.api.set_vad_silence_duration(durationSec);
      return { success: true };
    },

    async getWakeWordStatus() {
      if (this.isAvailable()) return await window.pywebview.api.get_wake_word_status();
      return { engine: "VAD + Whisper Spotter", is_enabled: true };
    },

    // Milestone 3: Memories, Tasks, Reminders
    async getMemories(search = null) {
      if (this.isAvailable()) return await window.pywebview.api.get_memories(search);
      return [];
    },

    async addMemory(content, category = "general") {
      if (this.isAvailable()) return await window.pywebview.api.add_memory(content, category);
      return { success: true };
    },

    async updateMemory(memoryId, content) {
      if (this.isAvailable()) return await window.pywebview.api.update_memory(memoryId, content);
      return { success: true };
    },

    async deleteMemory(memoryId) {
      if (this.isAvailable()) return await window.pywebview.api.delete_memory(memoryId);
      return { success: true };
    },

    async getTasks(completed = null) {
      if (this.isAvailable()) return await window.pywebview.api.get_tasks(completed);
      return [];
    },

    async addTask(title, dueDate = null) {
      if (this.isAvailable()) return await window.pywebview.api.add_task(title, dueDate);
      return { success: true };
    },

    async toggleTask(taskId, completed) {
      if (this.isAvailable()) return await window.pywebview.api.toggle_task(taskId, completed);
      return { success: true };
    },

    async deleteTask(taskId) {
      if (this.isAvailable()) return await window.pywebview.api.delete_task(taskId);
      return { success: true };
    },

    async getReminders(activeOnly = false) {
      if (this.isAvailable()) return await window.pywebview.api.get_reminders(activeOnly);
      return [];
    },

    async addReminder(title, remindAt) {
      if (this.isAvailable()) return await window.pywebview.api.add_reminder(title, remindAt);
      return { success: true };
    },

    async completeReminder(reminderId) {
      if (this.isAvailable()) return await window.pywebview.api.complete_reminder(reminderId);
      return { success: true };
    },

    async deleteReminder(reminderId) {
      if (this.isAvailable()) return await window.pywebview.api.delete_reminder(reminderId);
      return { success: true };
    },

    async checkDueReminders() {
      if (this.isAvailable()) return await window.pywebview.api.check_due_reminders();
      return [];
    }
  };

  // Helper to synchronize Mute UI states across header & modal
  function updateMuteUI(isMuted) {
    state.voiceMuted = isMuted;

    if (elements.btnMuteToggle) {
      elements.btnMuteToggle.classList.toggle('muted', isMuted);
      elements.btnMuteToggle.title = isMuted ? "Unmute Voice Output" : "Mute Voice Output";
    }
    if (elements.iconUnmuted) elements.iconUnmuted.classList.toggle('hidden', isMuted);
    if (elements.iconMuted) elements.iconMuted.classList.toggle('hidden', !isMuted);

    if (elements.btnModalMuteToggle) {
      elements.btnModalMuteToggle.textContent = isMuted ? "UNMUTE VOICE" : "MUTE VOICE";
    }
    if (elements.modalVoiceStatus) {
      elements.modalVoiceStatus.textContent = isMuted ? "Muted" : "Active // Ready";
      elements.modalVoiceStatus.style.color = isMuted ? "var(--status-amber)" : "var(--status-green)";
    }
  }

  // Visual state controller for Microphone button & HUD indicators
  function setMicVisualState(vState) {
    if (!elements.btnMic) return;
    elements.btnMic.classList.remove('listening', 'processing', 'recognized', 'error');

    if (vState === 'listening') {
      elements.btnMic.classList.add('listening');
      elements.btnMic.title = "Listening... Click to finish speaking";
      setCoreState("LISTENING", "WHISPER STT v1.0");
    } else if (vState === 'processing') {
      elements.btnMic.classList.add('processing');
      elements.btnMic.title = "Transcribing speech...";
      setCoreState("TRANSCRIBING", "FASTER-WHISPER INT8");
    } else if (vState === 'recognized') {
      elements.btnMic.classList.add('recognized');
      elements.btnMic.title = "Speech Recognized!";
      setCoreState("TRANSMITTING", "WHISPER STT v1.0");
    } else if (vState === 'error') {
      elements.btnMic.classList.add('error');
      elements.btnMic.title = "Microphone error / no speech detected";
      setCoreState("STANDBY", "LOCAL CORE");
    } else {
      elements.btnMic.title = "Voice Input: Click to Speak / Click to Stop";
      setCoreState("STANDBY", "LOCAL CORE");
    }
  }

  // ============================================================
  // CHAT INTERFACE & RENDERING
  // ============================================================
  function appendMessage(sender, text, timestamp = null) {
    if (!elements.messagesContainer) return;

    const timeStr = timestamp || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const isUser = sender.toUpperCase() === 'USER';

    const bubble = document.createElement('div');
    bubble.className = `msg-bubble ${isUser ? 'user' : 'edith'}`;

    const header = document.createElement('div');
    header.className = 'msg-header';

    const senderSpan = document.createElement('span');
    senderSpan.className = 'msg-sender';
    senderSpan.textContent = isUser ? state.userCallsign : 'E.D.I.T.H.';

    const timeSpan = document.createElement('span');
    timeSpan.className = 'msg-time';
    timeSpan.textContent = timeStr;

    if (isUser) {
      header.appendChild(timeSpan);
      header.appendChild(senderSpan);
    } else {
      header.appendChild(senderSpan);
      header.appendChild(timeSpan);
    }

    const content = document.createElement('div');
    content.className = 'msg-content';
    content.textContent = text;

    bubble.appendChild(header);
    bubble.appendChild(content);

    elements.messagesContainer.appendChild(bubble);
    elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;
  }

  function showTypingIndicator() {
    removeTypingIndicator();
    const ind = document.createElement('div');
    ind.className = 'typing-indicator';
    ind.id = 'active-typing-indicator';
    ind.innerHTML = `
      <span>E.D.I.T.H. ANALYZING</span>
      <span class="dot"></span>
      <span class="dot"></span>
      <span class="dot"></span>
    `;
    elements.messagesContainer.appendChild(ind);
    elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;
  }

  function removeTypingIndicator() {
    const existing = document.getElementById('active-typing-indicator');
    if (existing) existing.remove();
  }

  async function handleUserSubmit(e) {
    if (e) e.preventDefault();
    const text = elements.userInput.value.trim();
    if (!text || state.isProcessing) return;

    elements.userInput.value = '';
    playSoundChime('send');

    // Render User Message
    appendMessage('USER', text);

    // UI state
    setCoreState('ANALYZING');
    showTypingIndicator();

    try {
      // Direct call to Python backend via Bridge
      const response = await Bridge.sendMessage(text);

      removeTypingIndicator();
      setCoreState('TRANSMITTING');

      if (response && response.reply) {
        playSoundChime('receive');
        appendMessage('EDITH', response.reply, response.timestamp);
        loadArchiveCounts();
        if (state.archiveOpen) loadArchiveData();
      }

      setTimeout(() => setCoreState('STANDBY'), 800);
    } catch (err) {
      removeTypingIndicator();
      setCoreState('STANDBY');
      appendMessage('EDITH', `Bridge exception: ${err.message || err}`);
    }
  }

  // ============================================================
  // TELEMETRY REFRESH
  // ============================================================
  async function refreshTelemetry() {
    try {
      const data = await Bridge.getTelemetry();
      if (!data) return;

      // Header values
      if (elements.headerCpu) elements.headerCpu.textContent = `${data.cpu_percent}%`;
      if (elements.headerRam) elements.headerRam.textContent = `${data.ram_used_gb} GB`;
      if (elements.statusUptime && data.uptime) {
        elements.statusUptime.querySelector('.badge-text').textContent = `UPTIME: ${data.uptime}`;
      }

      // Telemetry Grid Cards
      if (elements.cardCpuVal) elements.cardCpuVal.textContent = `${data.cpu_percent}%`;
      if (elements.meterCpuFill) elements.meterCpuFill.style.width = `${Math.min(data.cpu_percent, 100)}%`;

      if (elements.cardRamVal) elements.cardRamVal.textContent = `${data.ram_used_gb} / ${data.ram_total_gb} GB (${data.ram_percent}%)`;
      if (elements.meterRamFill) elements.meterRamFill.style.width = `${Math.min(data.ram_percent, 100)}%`;

      if (elements.cardBatteryVal) elements.cardBatteryVal.textContent = `${data.battery_percent}% (${data.battery_status || 'Plugged'})`;
      if (elements.meterBatteryFill) elements.meterBatteryFill.style.width = `${Math.min(data.battery_percent, 100)}%`;

      if (elements.cardDiskVal) elements.cardDiskVal.textContent = `${data.disk_free_gb} GB Free (${data.disk_percent}% Used)`;
      if (elements.meterDiskFill) elements.meterDiskFill.style.width = `${Math.min(data.disk_percent, 100)}%`;

      // Voice & Wake-Word status synchronization (Milestone 4.4)
      if (data.hud_state && data.hud_state !== state.hudState) {
        applyHudState(data.hud_state, data.hud_details || "");
      }
      if (typeof data.wake_word_enabled !== 'undefined' && data.wake_word_enabled !== state.wakeWordEnabled) {
        updateWakeWordUI(data.wake_word_enabled);
      }

      // Check for due reminders (Milestone 3, Feature 4)
      const dueReminders = await Bridge.checkDueReminders();
      if (dueReminders && dueReminders.length > 0) {
        dueReminders.forEach(r => {
          playSoundChime('alert');
          appendMessage('EDITH', `⏰ TACTICAL REMINDER: ${r.title}`);
        });
        if (state.archiveOpen) loadArchiveData();
        loadArchiveCounts();
      }
    } catch (err) {
      console.warn("Telemetry fetch error:", err);
    }
  }

  // ============================================================
  // SETTINGS & THEMES
  // ============================================================
  function applyTheme(themeName) {
    state.currentTheme = themeName;
    document.body.classList.remove('theme-cyan', 'theme-amber', 'theme-stealth');
    document.body.classList.add(`theme-${themeName}`);

    elements.themeChoices.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.theme === themeName);
    });
  }

  function setupSettings() {
    // Open Settings
    elements.btnOpenSettings.addEventListener('click', () => {
      playSoundChime('click');
      elements.settingsModal.classList.add('active');
    });

    // Close Settings
    elements.btnCloseSettings.addEventListener('click', () => {
      elements.settingsModal.classList.remove('active');
    });

    // Theme pickers
    elements.themeChoices.forEach(btn => {
      btn.addEventListener('click', () => {
        playSoundChime('click');
        const theme = btn.dataset.theme;
        applyTheme(theme);
        Bridge.saveSetting('theme', theme);
      });
    });

    // Sound FX toggle
    elements.settingSoundFx.addEventListener('change', (e) => {
      state.soundEnabled = e.target.checked;
      Bridge.saveSetting('sound_effects', state.soundEnabled);
    });

    // Test Voice Button (Milestone 2A)
    if (elements.btnTestVoice) {
      elements.btnTestVoice.addEventListener('click', async () => {
        playSoundChime('click');
        setCoreState('TRANSMITTING');
        await Bridge.testVoice();
        setTimeout(() => setCoreState('STANDBY'), 3000);
      });
    }

    // Modal Mute Toggle Button
    if (elements.btnModalMuteToggle) {
      elements.btnModalMuteToggle.addEventListener('click', async () => {
        playSoundChime('click');
        const isMuted = await Bridge.toggleMute();
        updateMuteUI(isMuted);
      });
    }

    // Header Hands-Free Wake-Word Toggle Button (Milestone 4.4)
    if (elements.btnWakeWordToggle) {
      elements.btnWakeWordToggle.addEventListener('click', async () => {
        playSoundChime('click');
        const res = await Bridge.toggleWakeWord();
        if (res && typeof res.enabled !== 'undefined') {
          updateWakeWordUI(res.enabled);
        }
      });
    }

    // Modal Hands-Free Wake-Word Toggle Switch (Milestone 4.4)
    if (elements.settingWakeWord) {
      elements.settingWakeWord.addEventListener('change', async (e) => {
        const checked = e.target.checked;
        await Bridge.setWakeWordEnabled(checked);
        updateWakeWordUI(checked);
      });
    }

    // Modal Silence Timeout setting (Milestone 4.4)
    if (elements.settingSilenceTimeout) {
      elements.settingSilenceTimeout.addEventListener('change', async (e) => {
        const val = parseFloat(e.target.value) || 1.5;
        await Bridge.setVadSilenceDuration(val);
      });
    }

    // Save Settings Button
    elements.btnSaveSettings.addEventListener('click', () => {
      playSoundChime('click');
      const newCallsign = elements.settingCallsign.value.trim() || 'Boss';
      state.userCallsign = newCallsign;
      Bridge.saveSetting('user_callsign', newCallsign);

      if (elements.settingWakeWord) {
        const wwVal = elements.settingWakeWord.checked;
        Bridge.setWakeWordEnabled(wwVal);
        updateWakeWordUI(wwVal);
      }
      if (elements.settingSilenceTimeout) {
        const sVal = parseFloat(elements.settingSilenceTimeout.value) || 1.5;
        Bridge.setVadSilenceDuration(sVal);
      }

      elements.settingsModal.classList.remove('active');
      appendMessage('EDITH', `System parameters updated. Acknowledged, ${state.userCallsign}.`);
    });

    // Clear Chat
    elements.btnClearChat.addEventListener('click', async () => {
      playSoundChime('click');
      await Bridge.clearHistory();
      elements.messagesContainer.innerHTML = '';
      appendMessage('EDITH', `Conversation memory wiped. Display buffer cleared, ${state.userCallsign}.`);
    });
  }

  // ============================================================
  // EVENT LISTENERS & CHIP DIRECTIVES
  // ============================================================
  function setupEvents() {
    elements.chatForm.addEventListener('submit', handleUserSubmit);

    // Header Mute Toggle Button
    if (elements.btnMuteToggle) {
      elements.btnMuteToggle.addEventListener('click', async () => {
        playSoundChime('click');
        const isMuted = await Bridge.toggleMute();
        updateMuteUI(isMuted);
      });
    }

    // Quick command chips
    elements.chipButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const prompt = btn.dataset.prompt;
        if (prompt) {
          elements.userInput.value = prompt;
          handleUserSubmit();
        }
      });
    });

    // Live Offline Microphone Speech-To-Text (Milestone 2B)
    if (elements.btnMic) {
      elements.btnMic.addEventListener('click', async (e) => {
        if (e) {
          e.preventDefault();
          e.stopPropagation();
        }
        if (state.isStartingMic || state.isTranscribing) return;

        if (!state.isRecording) {
          // START RECORDING
          playSoundChime('click');
          state.isStartingMic = true;
          state.isRecording = true;
          setMicVisualState('listening');

          try {
            console.log('[EDITH Voice] Starting microphone capture stream...');
            const res = await Bridge.startMic();
            state.isStartingMic = false;
            if (res && res.status === 'error') {
              state.isRecording = false;
              setMicVisualState('error');
              appendMessage('EDITH', `Microphone Notice: ${res.message || 'Input device unavailable.'}`);
              setTimeout(() => setMicVisualState('ready'), 2500);
            }
          } catch (e) {
            state.isStartingMic = false;
            state.isRecording = false;
            setMicVisualState('error');
            setTimeout(() => setMicVisualState('ready'), 2000);
          }
        } else {
          // STOP RECORDING & TRANSCRIBE
          playSoundChime('click');
          state.isRecording = false;
          state.isTranscribing = true;
          setMicVisualState('processing');

          try {
            console.log('[EDITH Voice] Stopping microphone and transcribing via Faster-Whisper...');
            const result = await Bridge.stopMic();
            state.isTranscribing = false;

            if (result && result.status === 'recognized' && result.text) {
              setMicVisualState('recognized');
              elements.userInput.value = result.text;
              setTimeout(() => setMicVisualState('ready'), 600);
              // Transmit speech prompt automatically into the assistant pipeline
              handleUserSubmit();
            } else if (result && result.status === 'silent') {
              setMicVisualState('ready');
              elements.userInput.placeholder = "No speech detected. Click mic to try speaking again.";
              setTimeout(() => {
                elements.userInput.placeholder = "Speak or type your command, Boss...";
              }, 3000);
            } else if (result && result.status === 'too_short') {
              setMicVisualState('ready');
            } else {
              setMicVisualState('error');
              setTimeout(() => setMicVisualState('ready'), 1500);
            }
          } catch (err) {
            state.isTranscribing = false;
            setMicVisualState('error');
            setTimeout(() => setMicVisualState('ready'), 1500);
          }
        }
      });
    }

    // Keyboard shortcuts: Escape closes modals
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        if (elements.settingsModal && elements.settingsModal.classList.contains('active')) {
          elements.settingsModal.classList.remove('active');
        }
        if (elements.archiveModal && elements.archiveModal.classList.contains('active')) {
          state.archiveOpen = false;
          elements.archiveModal.classList.remove('active');
        }
      }
    });
  }

  // ============================================================
  // TACTICAL ARCHIVE CONTROLLER (Milestone 3)
  // ============================================================
  function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  async function loadArchiveCounts() {
    try {
      const [mems, tasks, rems] = await Promise.all([
        Bridge.getMemories(),
        Bridge.getTasks(),
        Bridge.getReminders(true)
      ]);
      if (elements.countMemories) elements.countMemories.textContent = mems.length;
      if (elements.countTasks) elements.countTasks.textContent = tasks.filter(t => !t.completed).length;
      if (elements.countReminders) elements.countReminders.textContent = rems.length;
    } catch (e) {
      console.warn("Error loading archive counts:", e);
    }
  }

  async function loadMemories(searchTerm = null) {
    if (!elements.memoriesList) return;
    try {
      const memories = await Bridge.getMemories(searchTerm);
      if (elements.countMemories) elements.countMemories.textContent = memories.length;

      if (!memories || memories.length === 0) {
        elements.memoriesList.innerHTML = `<div class="archive-empty">NO ARCHIVED MEMORIES FOUND</div>`;
        return;
      }

      elements.memoriesList.innerHTML = '';
      memories.forEach(m => {
        const item = document.createElement('div');
        item.className = 'archive-item';
        item.dataset.id = m.id;

        const dateStr = m.created_at ? m.created_at.replace('T', ' ').substring(0, 16) : '';
        item.innerHTML = `
          <div class="item-left">
            <div class="item-info">
              <span class="item-title">${escapeHtml(m.content)}</span>
              <span class="item-meta">ARCHIVED: ${dateStr} // CAT: ${escapeHtml(m.category || 'general')}</span>
            </div>
          </div>
          <div class="item-actions">
            <button class="icon-action-btn edit" title="Edit Memory" data-id="${m.id}" data-content="${escapeHtml(m.content)}">&#9998;</button>
            <button class="icon-action-btn delete" title="Delete Memory" data-id="${m.id}">&#128465;</button>
          </div>
        `;
        elements.memoriesList.appendChild(item);
      });
    } catch (e) {
      console.error("Error loading memories:", e);
    }
  }

  async function loadTasks(filter = 'all') {
    if (!elements.tasksList) return;
    try {
      state.activeTaskFilter = filter;
      const compParam = filter === 'all' ? null : (filter === 'completed');
      const tasks = await Bridge.getTasks(compParam);
      if (elements.countTasks) {
        const pendingTasks = await Bridge.getTasks(false);
        elements.countTasks.textContent = pendingTasks.length;
      }

      if (!tasks || tasks.length === 0) {
        elements.tasksList.innerHTML = `<div class="archive-empty">NO TASKS IN RADAR</div>`;
        return;
      }

      elements.tasksList.innerHTML = '';
      tasks.forEach(t => {
        const item = document.createElement('div');
        item.className = `archive-item ${t.completed ? 'completed' : ''}`;
        item.dataset.id = t.id;

        const dueStr = t.due_date ? ` // DUE: ${escapeHtml(t.due_date)}` : '';
        item.innerHTML = `
          <div class="item-left">
            <input type="checkbox" class="item-checkbox" data-id="${t.id}" ${t.completed ? 'checked' : ''} />
            <div class="item-info">
              <span class="item-title">${escapeHtml(t.title)}</span>
              <span class="item-meta">${t.completed ? '[COMPLETED]' : '[PENDING]'}${dueStr}</span>
            </div>
          </div>
          <div class="item-actions">
            <button class="icon-action-btn delete" title="Delete Task" data-id="${t.id}">&#128465;</button>
          </div>
        `;
        elements.tasksList.appendChild(item);
      });
    } catch (e) {
      console.error("Error loading tasks:", e);
    }
  }

  async function loadReminders() {
    if (!elements.remindersList) return;
    try {
      const reminders = await Bridge.getReminders(false);
      if (elements.countReminders) {
        elements.countReminders.textContent = reminders.filter(r => !r.is_completed).length;
      }

      if (!reminders || reminders.length === 0) {
        elements.remindersList.innerHTML = `<div class="archive-empty">NO ACTIVE REMINDERS SCHEDULED</div>`;
        return;
      }

      const nowIso = new Date().toISOString();
      elements.remindersList.innerHTML = '';
      reminders.forEach(r => {
        const item = document.createElement('div');
        const isPast = r.remind_at <= nowIso && !r.is_completed;
        item.className = `archive-item ${r.is_completed ? 'completed' : ''}`;
        item.dataset.id = r.id;

        let badgeClass = 'badge-active';
        let badgeText = 'ACTIVE';
        if (r.is_completed) {
          badgeClass = 'badge-completed';
          badgeText = 'DISMISSED';
        } else if (isPast) {
          badgeClass = 'badge-overdue';
          badgeText = 'OVERDUE';
        }

        const timeStr = r.remind_at ? new Date(r.remind_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' }) : '';
        item.innerHTML = `
          <div class="item-left">
            <div class="item-info">
              <span class="item-title">${escapeHtml(r.title)}</span>
              <span class="item-meta">
                <span class="badge-tag ${badgeClass}">${badgeText}</span>
                ${timeStr}
              </span>
            </div>
          </div>
          <div class="item-actions">
            ${!r.is_completed ? `<button class="icon-action-btn complete" title="Mark Done" data-id="${r.id}">✓</button>` : ''}
            <button class="icon-action-btn delete" title="Delete Reminder" data-id="${r.id}">&#128465;</button>
          </div>
        `;
        elements.remindersList.appendChild(item);
      });
    } catch (e) {
      console.error("Error loading reminders:", e);
    }
  }

  async function loadArchiveData() {
    await Promise.all([
      loadMemories(elements.searchMemories ? elements.searchMemories.value : null),
      loadTasks(state.activeTaskFilter),
      loadReminders()
    ]);
  }

  function setupArchive() {
    // Open Archive Modal
    if (elements.btnOpenArchive) {
      elements.btnOpenArchive.addEventListener('click', () => {
        playSoundChime('click');
        state.archiveOpen = true;
        elements.archiveModal.classList.add('active');
        loadArchiveData();
      });
    }

    // Close Archive Modal
    if (elements.btnCloseArchive) {
      elements.btnCloseArchive.addEventListener('click', () => {
        state.archiveOpen = false;
        elements.archiveModal.classList.remove('active');
      });
    }

    // Tab Navigation
    elements.archiveTabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        playSoundChime('click');
        const targetTab = btn.dataset.tab;
        elements.archiveTabBtns.forEach(b => b.classList.remove('active'));
        elements.archiveTabPanes.forEach(p => p.classList.remove('active'));

        btn.classList.add('active');
        const pane = document.getElementById(targetTab);
        if (pane) pane.classList.add('active');
      });
    });

    // 1. Memories handlers
    if (elements.btnAddMemory && elements.inputNewMemory) {
      const handleAddMem = async () => {
        const text = elements.inputNewMemory.value.trim();
        if (!text) return;
        playSoundChime('click');
        const res = await Bridge.addMemory(text);
        if (res && res.error) {
          alert(res.error);
        } else {
          elements.inputNewMemory.value = '';
          loadMemories();
        }
      };
      elements.btnAddMemory.addEventListener('click', handleAddMem);
      elements.inputNewMemory.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          handleAddMem();
        }
      });
    }

    if (elements.searchMemories) {
      elements.searchMemories.addEventListener('input', (e) => {
        loadMemories(e.target.value);
      });
    }

    if (elements.memoriesList) {
      elements.memoriesList.addEventListener('click', async (e) => {
        const editBtn = e.target.closest('.icon-action-btn.edit');
        const delBtn = e.target.closest('.icon-action-btn.delete');

        if (editBtn) {
          const id = editBtn.dataset.id;
          const oldContent = editBtn.dataset.content;
          const updated = prompt("Edit Memory Entry:", oldContent);
          if (updated && updated.trim() && updated.trim() !== oldContent) {
            playSoundChime('click');
            await Bridge.updateMemory(id, updated.trim());
            loadMemories();
          }
        } else if (delBtn) {
          const id = delBtn.dataset.id;
          if (confirm("Delete this archived memory?")) {
            playSoundChime('click');
            await Bridge.deleteMemory(id);
            loadMemories();
          }
        }
      });
    }

    // 2. Tasks handlers
    if (elements.btnAddTask && elements.inputNewTask) {
      const handleAddTask = async () => {
        const title = elements.inputNewTask.value.trim();
        const due = elements.inputTaskDue ? elements.inputTaskDue.value.trim() : null;
        if (!title) return;
        playSoundChime('click');
        await Bridge.addTask(title, due || null);
        elements.inputNewTask.value = '';
        if (elements.inputTaskDue) elements.inputTaskDue.value = '';
        loadTasks(state.activeTaskFilter);
      };
      elements.btnAddTask.addEventListener('click', handleAddTask);
      elements.inputNewTask.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          handleAddTask();
        }
      });
    }

    elements.taskFilterBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        playSoundChime('click');
        elements.taskFilterBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const filter = btn.dataset.filter;
        loadTasks(filter);
      });
    });

    if (elements.tasksList) {
      elements.tasksList.addEventListener('click', async (e) => {
        const chk = e.target.closest('.item-checkbox');
        const delBtn = e.target.closest('.icon-action-btn.delete');

        if (chk) {
          const id = chk.dataset.id;
          const completed = chk.checked;
          playSoundChime('click');
          await Bridge.toggleTask(id, completed);
          loadTasks(state.activeTaskFilter);
        } else if (delBtn) {
          const id = delBtn.dataset.id;
          if (confirm("Delete this task from radar?")) {
            playSoundChime('click');
            await Bridge.deleteTask(id);
            loadTasks(state.activeTaskFilter);
          }
        }
      });
    }

    // 3. Reminders handlers
    if (elements.btnAddReminder && elements.inputNewReminder) {
      elements.btnAddReminder.addEventListener('click', async () => {
        const title = elements.inputNewReminder.value.trim();
        const timeVal = elements.inputReminderTime ? elements.inputReminderTime.value : null;
        if (!title || !timeVal) {
          alert("Please enter both reminder title and date/time.");
          return;
        }
        playSoundChime('click');
        await Bridge.addReminder(title, new Date(timeVal).toISOString());
        elements.inputNewReminder.value = '';
        if (elements.inputReminderTime) elements.inputReminderTime.value = '';
        loadReminders();
      });
    }

    if (elements.remindersList) {
      elements.remindersList.addEventListener('click', async (e) => {
        const compBtn = e.target.closest('.icon-action-btn.complete');
        const delBtn = e.target.closest('.icon-action-btn.delete');

        if (compBtn) {
          const id = compBtn.dataset.id;
          playSoundChime('click');
          await Bridge.completeReminder(id);
          loadReminders();
        } else if (delBtn) {
          const id = delBtn.dataset.id;
          if (confirm("Delete this scheduled reminder?")) {
            playSoundChime('click');
            await Bridge.deleteReminder(id);
            loadReminders();
          }
        }
      });
    }
  }

  // ============================================================
  // INITIALIZATION LIFECYCLE
  // ============================================================
  async function startup() {
    if (state.initialized) return;
    state.initialized = true;
    state.bridgeReady = true;

    initVisualizer();
    setupEvents();
    setupSettings();
    setupArchive();
    loadArchiveCounts();

    // Check saved settings & system metadata
    try {
      const sysInfo = await Bridge.getSystemInfo();
      if (sysInfo && sysInfo.mic_device) {
        const micEl = document.getElementById('modal-mic-name');
        if (micEl) micEl.textContent = `Input: ${sysInfo.mic_device}`;
      }

      const saved = await Bridge.getSettings();
      if (saved) {
        if (saved.theme) applyTheme(saved.theme);
        if (saved.user_callsign) {
          state.userCallsign = saved.user_callsign;
          if (elements.settingCallsign) elements.settingCallsign.value = saved.user_callsign;
        }
        if (typeof saved.sound_effects !== 'undefined') {
          state.soundEnabled = saved.sound_effects;
          if (elements.settingSoundFx) elements.settingSoundFx.checked = saved.sound_effects;
        }
        if (typeof saved.voice_muted !== 'undefined') {
          updateMuteUI(Boolean(saved.voice_muted));
        }
        if (typeof saved.wake_word_enabled !== 'undefined') {
          updateWakeWordUI(Boolean(saved.wake_word_enabled));
        }
        if (saved.vad_silence_duration && elements.settingSilenceTimeout) {
          elements.settingSilenceTimeout.value = saved.vad_silence_duration;
        }
      }

      // Check conversation history
      const history = await Bridge.getHistory();
      if (history && history.length > 0) {
        history.forEach(m => {
          appendMessage(m.sender, m.text, m.timestamp ? new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : null);
        });
      } else {
        // First-run cinematic greeting
        appendMessage('EDITH', `Greetings, ${state.userCallsign}. E.D.I.T.H. initialized in Milestone 4.4 mode. Hands-free voice activation is active: say "Hey EDITH" to command me.`);
      }
    } catch (e) {
      appendMessage('EDITH', `Greetings, ${state.userCallsign}. EDITH online.`);
    }

    // Telemetry polling
    refreshTelemetry();
    state.telemetryTimer = setInterval(refreshTelemetry, 2500);

    // Initial audio chime
    setTimeout(() => playSoundChime('startup'), 300);
  }

  // Attach to PyWebView bridge ready event or window load
  if (window.pywebview) {
    startup();
  } else {
    window.addEventListener('pywebviewready', () => startup());
    window.addEventListener('DOMContentLoaded', () => {
      // If pywebview doesn't fire within 400ms, start in standalone mode
      setTimeout(() => {
        startup();
      }, 400);
    });
  }
})();
