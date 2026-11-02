/* ============================================================
   E.D.I.T.H. HUD Controller & Bridge Interface
   Milestone 1: Desktop Shell, Holographic Canvas & Telemetry
   ============================================================ */

(() => {
  // Application State
  const state = {
    bridgeReady: false,
    soundEnabled: true,
    userCallsign: "Boss",
    currentTheme: "cyan",
    telemetryTimer: null,
    isProcessing: false,
    audioContext: null
  };

  // DOM Elements
  const elements = {
    // Header
    headerCpu: document.getElementById('header-cpu-val'),
    headerRam: document.getElementById('header-ram-val'),
    statusUptime: document.getElementById('status-uptime'),
    statusProtocol: document.getElementById('status-protocol'),
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
    settingCallsign: document.getElementById('setting-callsign'),
    settingSoundFx: document.getElementById('setting-sound-fx'),
    themeChoices: document.querySelectorAll('.theme-choice'),
    chipButtons: document.querySelectorAll('.chip-btn')
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

    if (status === "ANALYZING" || status === "PROCESSING") {
      state.isProcessing = true;
      waveIntensity = 2.8;
    } else {
      state.isProcessing = false;
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
        sound_effects: state.soundEnabled
      };
    },

    async saveSetting(key, value) {
      if (this.isAvailable()) return await window.pywebview.api.save_setting(key, value);
      return { success: true };
    }
  };

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

    // Save Settings Button
    elements.btnSaveSettings.addEventListener('click', () => {
      playSoundChime('click');
      const newCallsign = elements.settingCallsign.value.trim() || 'Boss';
      state.userCallsign = newCallsign;
      Bridge.saveSetting('user_callsign', newCallsign);
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

    // Mic Button Placeholder for M2
    elements.btnMic.addEventListener('click', () => {
      playSoundChime('click');
      elements.btnMic.classList.toggle('listening');
      if (elements.btnMic.classList.contains('listening')) {
        appendMessage('EDITH', `Audio intake simulated. Local Whisper speech-to-text is scheduled for Milestone 2. Switching to console keyboard input.`);
        setTimeout(() => {
          elements.btnMic.classList.remove('listening');
        }, 3000);
      }
    });

    // Keyboard shortcuts: Escape closes modal
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && elements.settingsModal.classList.contains('active')) {
        elements.settingsModal.classList.remove('active');
      }
    });
  }

  // ============================================================
  // INITIALIZATION LIFECYCLE
  // ============================================================
  async function startup() {
    initVisualizer();
    setupEvents();
    setupSettings();

    // Check saved settings
    try {
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
      }

      // Check conversation history
      const history = await Bridge.getHistory();
      if (history && history.length > 0) {
        history.forEach(m => {
          appendMessage(m.sender, m.text, m.timestamp ? new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : null);
        });
      } else {
        // First-run cinematic greeting
        appendMessage('EDITH', `Greetings, ${state.userCallsign}. E.D.I.T.H. initialized in Milestone 1 mode. All local security protocols are active and telemetry channels are online.`);
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
    window.addEventListener('pywebviewready', startup);
    window.addEventListener('DOMContentLoaded', () => {
      // If pywebview doesn't fire within 400ms, start in standalone mode
      setTimeout(() => {
        if (!state.bridgeReady) {
          state.bridgeReady = true;
          startup();
        }
      }, 400);
    });
  }
})();
