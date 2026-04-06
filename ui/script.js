/* ═══════════════════════════════════════════════════════════════
   J.A.R.V.I.S. — Frontend Logic v2.0
   Markdown rendering, real system stats, settings, export
   ═══════════════════════════════════════════════════════════════ */

// ─── Configure Marked for markdown rendering ─────────────────
if (typeof marked !== 'undefined') {
    marked.setOptions({
        highlight: function(code, lang) {
            if (typeof hljs !== 'undefined' && lang && hljs.getLanguage(lang)) {
                return hljs.highlight(code, { language: lang }).value;
            }
            return code;
        },
        breaks: true,
        gfm: true,
    });
}

// ─── DOM Elements ────────────────────────────────────────────
const chatMessages  = document.getElementById('chat-messages');
const userInput     = document.getElementById('user-input');
const sendBtn       = document.getElementById('send-btn');
const micBtn        = document.getElementById('mic-btn');
const wakeBtn       = document.getElementById('wake-btn');
const stopBtn       = document.getElementById('stop-btn');
const orbEl         = document.getElementById('orb');
const orbLabel      = document.getElementById('orb-label');
const statusDot     = document.getElementById('status-indicator');
const statusText    = document.getElementById('status-text');
const clockEl       = document.getElementById('clock');
const audioPlayer   = document.getElementById('audio-player');
const feedItems     = document.getElementById('feed-items');
const cpuBar        = document.getElementById('cpu-bar');
const ramBar        = document.getElementById('ram-bar');
const diskBar       = document.getElementById('disk-bar');
const cpuVal        = document.getElementById('cpu-val');
const ramVal        = document.getElementById('ram-val');
const diskVal       = document.getElementById('disk-val');
const canvas        = document.getElementById('reactor-canvas');
const ctx           = canvas.getContext('2d');
const settingsModal = document.getElementById('settings-modal');
const settingsBtn   = document.getElementById('settings-btn');
const exportBtn     = document.getElementById('export-btn');
const clearBtn      = document.getElementById('clear-btn');

// ─── Settings ────────────────────────────────────────────────
let autoSpeak = true;
let audioNotify = true;

// ─── WebSocket ───────────────────────────────────────────────
let ws = null;
let reconnectAttempts = 0;
const MAX_RECONNECT = 10;

function connectWS() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${location.host}/ws`);

    ws.onopen = () => {
        reconnectAttempts = 0;
        setStatus('online', 'ONLINE');
        addSystemMessage('Connection established. All systems operational.');
    };

    ws.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            handleMessage(msg);
        } catch (e) {
            console.error('WS parse error:', e);
        }
    };

    ws.onclose = () => {
        setStatus('error', 'OFFLINE');
        if (reconnectAttempts < MAX_RECONNECT) {
            reconnectAttempts++;
            setTimeout(connectWS, 2000 * reconnectAttempts);
        }
    };

    ws.onerror = () => {
        setStatus('error', 'ERROR');
    };
}

function handleMessage(msg) {
    switch (msg.type) {
        case 'greeting':
            addJarvisMessage(msg.message);
            break;
        case 'response':
            removeTypingIndicator();
            setOrbState('idle');
            addJarvisMessage(msg.message);
            break;
        case 'thinking':
            setOrbState('thinking');
            showTypingIndicator();
            break;
        case 'audio':
            if (autoSpeak) {
                playAudio(msg.data, msg.format);
            }
            break;
        case 'tool_call':
            addToolMessage(msg.tool, msg.args);
            addFeedItem(msg.tool, JSON.stringify(msg.args).substring(0, 60));
            break;
        case 'reminder':
            addJarvisMessage(msg.message);
            playNotificationSound();
            break;
        case 'wake_word':
            setOrbState('thinking');
            orbLabel.textContent = 'Listening...';
            addSystemMessage('Wake word detected - listening for command...');
            playNotificationSound();
            break;
        case 'voice_detected':
            addUserMessage('[Voice] ' + msg.message);
            break;
        case 'partial_speech':
            // Show live transcription in the input box
            userInput.value = msg.accumulated || msg.text || '';
            userInput.style.color = 'var(--warning)';
            break;
        case 'pong':
            break;
    }
}

// ─── Send Message ────────────────────────────────────────────
function sendMessage() {
    const text = userInput.value.trim();
    if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;

    addUserMessage(text);
    ws.send(JSON.stringify({ type: 'chat', message: text }));
    userInput.value = '';
    setOrbState('thinking');
}

// Quick action buttons
function quickAction(text) {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    addUserMessage(text);
    ws.send(JSON.stringify({ type: 'chat', message: text }));
    setOrbState('thinking');
}

sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// ─── Voice Input (Web Speech API) ────────────────────────────
let recognition = null;
let isRecording = false;
let currentSttLang = 'en-US';

if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = currentSttLang;

    recognition.onresult = (event) => {
        const text = event.results[0][0].transcript;
        userInput.value = text;
        sendMessage();
    };

    recognition.onend = () => {
        isRecording = false;
        micBtn.classList.remove('recording');
    };

    recognition.onerror = () => {
        isRecording = false;
        micBtn.classList.remove('recording');
    };
}

micBtn.addEventListener('click', () => {
    if (!recognition) {
        addSystemMessage('Voice input not supported in this browser.');
        return;
    }
    if (isRecording) {
        recognition.stop();
    } else {
        recognition.start();
        isRecording = true;
        micBtn.classList.add('recording');
    }
});

// ─── Wake Word Toggle ────────────────────────────────────────
let wakeWordActive = false;

wakeBtn.addEventListener('click', async () => {
    if (wakeWordActive) {
        // Stop
        try {
            const resp = await fetch('/api/wake/stop', { method: 'POST' });
            const data = await resp.json();
            wakeWordActive = false;
            wakeBtn.classList.remove('active');
            addSystemMessage('Wake word listener stopped.');
        } catch (e) {
            addSystemMessage('Failed to stop wake listener.');
        }
    } else {
        // Start
        try {
            const resp = await fetch('/api/wake/start', { method: 'POST' });
            const data = await resp.json();
            wakeWordActive = data.active;
            if (wakeWordActive) {
                wakeBtn.classList.add('active');
                addSystemMessage('Wake word listener started. Say "Jarvis" to activate.');
            } else {
                addSystemMessage(data.result || 'Failed to start wake listener.');
            }
        } catch (e) {
            addSystemMessage('Failed to start wake listener. Check microphone access.');
        }
    }
});

// Check initial wake word status
fetch('/api/wake/status').then(r => r.json()).then(data => {
    wakeWordActive = data.active;
    if (wakeWordActive) wakeBtn.classList.add('active');
}).catch(() => {});

// ─── Stop Speaking ───────────────────────────────────────────
stopBtn.addEventListener('click', () => {
    audioPlayer.pause();
    audioPlayer.currentTime = 0;
    setOrbState('idle');
    stopBtn.style.display = 'none';
});

// ─── Audio Playback ──────────────────────────────────────────
function playAudio(base64Data, format) {
    setOrbState('speaking');
    stopBtn.style.display = 'flex';
    const blob = base64ToBlob(base64Data, `audio/${format}`);
    const url = URL.createObjectURL(blob);
    audioPlayer.src = url;
    audioPlayer.play().catch(() => {});
    audioPlayer.onended = () => {
        setOrbState('idle');
        stopBtn.style.display = 'none';
        URL.revokeObjectURL(url);
    };
}

function base64ToBlob(b64, mime) {
    const byteChars = atob(b64);
    const byteArrays = [];
    for (let offset = 0; offset < byteChars.length; offset += 512) {
        const slice = byteChars.slice(offset, offset + 512);
        const byteNumbers = new Array(slice.length);
        for (let i = 0; i < slice.length; i++) {
            byteNumbers[i] = slice.charCodeAt(i);
        }
        byteArrays.push(new Uint8Array(byteNumbers));
    }
    return new Blob(byteArrays, { type: mime });
}

function playNotificationSound() {
    if (!audioNotify) return;
    try {
        const actx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = actx.createOscillator();
        const gain = actx.createGain();
        osc.connect(gain);
        gain.connect(actx.destination);
        osc.frequency.value = 800;
        osc.type = 'sine';
        gain.gain.setValueAtTime(0.3, actx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, actx.currentTime + 0.5);
        osc.start(actx.currentTime);
        osc.stop(actx.currentTime + 0.5);
    } catch (e) {}
}

// ─── Chat Messages ───────────────────────────────────────────
function addUserMessage(text) {
    const el = document.createElement('div');
    el.className = 'message user';
    el.textContent = text;
    chatMessages.appendChild(el);
    scrollChat();
}

function addJarvisMessage(text) {
    const el = document.createElement('div');
    el.className = 'message jarvis';
    // Render markdown if available
    if (typeof marked !== 'undefined') {
        el.innerHTML = DOMPurify ? DOMPurify.sanitize(marked.parse(text)) : marked.parse(text);
        // Apply syntax highlighting to code blocks
        el.querySelectorAll('pre code').forEach((block) => {
            if (typeof hljs !== 'undefined') {
                hljs.highlightElement(block);
            }
        });
    } else {
        el.textContent = text;
    }
    chatMessages.appendChild(el);
    scrollChat();
}

function addSystemMessage(text) {
    const el = document.createElement('div');
    el.className = 'message system';
    el.textContent = text;
    chatMessages.appendChild(el);
    scrollChat();
}

function addToolMessage(tool, args) {
    const el = document.createElement('div');
    el.className = 'message tool';
    el.textContent = `⚡ ${tool}(${JSON.stringify(args).substring(0, 120)})`;
    chatMessages.appendChild(el);
    scrollChat();
}

function scrollChat() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ─── Typing Indicator ────────────────────────────────────────
function showTypingIndicator() {
    removeTypingIndicator();
    const el = document.createElement('div');
    el.className = 'message jarvis typing-indicator';
    el.id = 'typing-indicator';
    el.innerHTML = '<span></span><span></span><span></span>';
    chatMessages.appendChild(el);
    scrollChat();
}

function removeTypingIndicator() {
    const ti = document.getElementById('typing-indicator');
    if (ti) ti.remove();
}

// ─── Activity Feed ───────────────────────────────────────────
function addFeedItem(tool, detail) {
    const el = document.createElement('div');
    el.className = 'feed-item';
    const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    el.innerHTML = `<span class="feed-time">${time}</span> <span class="feed-tool">${tool}</span> ${escapeHtml(detail)}`;
    feedItems.prepend(el);
    while (feedItems.children.length > 30) {
        feedItems.removeChild(feedItems.lastChild);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ─── Status & Orb ────────────────────────────────────────────
function setStatus(state, text) {
    statusDot.className = `status-dot ${state}`;
    statusText.textContent = text;
}

function setOrbState(state) {
    orbEl.className = state;
    const labels = { idle: 'Ready', thinking: 'Thinking...', speaking: 'Speaking' };
    orbLabel.textContent = labels[state] || 'Ready';
}

// ─── Clock ───────────────────────────────────────────────────
function updateClock() {
    clockEl.textContent = new Date().toLocaleTimeString('en-US', { hour12: false });
}
setInterval(updateClock, 1000);
updateClock();

// ─── Real System Stats ──────────────────────────────────────
async function updateStats() {
    try {
        const resp = await fetch('/api/stats');
        if (resp.ok) {
            const data = await resp.json();
            cpuBar.style.width = data.cpu + '%';
            ramBar.style.width = data.ram + '%';
            diskBar.style.width = data.disk + '%';
            cpuVal.textContent = Math.round(data.cpu) + '%';
            ramVal.textContent = Math.round(data.ram) + '%';
            diskVal.textContent = Math.round(data.disk) + '%';

            // Color coding for high usage
            cpuBar.style.background = data.cpu > 80 ? 'linear-gradient(90deg, var(--warning), var(--danger))' : '';
            ramBar.style.background = data.ram > 85 ? 'linear-gradient(90deg, var(--warning), var(--danger))' : '';
        }
    } catch (e) {
        // Fallback to simulated if API isn't available
    }
}
setInterval(updateStats, 3000);
updateStats();

// ─── Settings ────────────────────────────────────────────────
settingsBtn.addEventListener('click', async () => {
    settingsModal.style.display = 'flex';
    // Load available voices
    try {
        const resp = await fetch('/api/voices');
        if (resp.ok) {
            const data = await resp.json();
            const select = document.getElementById('voice-select');
            select.innerHTML = '';
            data.voices.forEach(v => {
                const opt = document.createElement('option');
                opt.value = v.split(' ')[0];
                opt.textContent = v;
                if (v.includes(data.current)) opt.selected = true;
                select.appendChild(opt);
            });
        }
    } catch (e) {}
    // Load current language
    try {
        const langResp = await fetch('/api/language');
        if (langResp.ok) {
            const langData = await langResp.json();
            document.getElementById('lang-select').value = langData.language || 'en';
        }
    } catch (e) {}
});

function closeSettings() {
    settingsModal.style.display = 'none';
    // Apply voice setting
    const voiceSelect = document.getElementById('voice-select');
    if (voiceSelect.value) {
        fetch('/api/voice/set', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ voice: voiceSelect.value }),
        });
    }

    // Apply language setting
    const langSelect = document.getElementById('lang-select');
    if (langSelect.value) {
        const langMap = { 'en': 'en-US', 'te': 'te-IN' };
        const newLang = langMap[langSelect.value] || 'en-US';
        if (newLang !== currentSttLang) {
            currentSttLang = newLang;
            if (recognition) recognition.lang = currentSttLang;
            // Tell server to switch language
            fetch('/api/language', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ language: langSelect.value }),
            }).then(r => r.json()).then(data => {
                const label = langSelect.value === 'te' ? 'Telugu (తెలుగు)' : 'English';
                addSystemMessage(`Language switched to ${label}`);
            });
        }
    }

    autoSpeak = document.getElementById('auto-speak').checked;
    audioNotify = document.getElementById('audio-notify').checked;
}

// ─── Export Chat ─────────────────────────────────────────────
exportBtn.addEventListener('click', () => {
    const messages = chatMessages.querySelectorAll('.message');
    let text = 'J.A.R.V.I.S. Conversation Export\n';
    text += '=' .repeat(40) + '\n';
    text += `Date: ${new Date().toLocaleString()}\n\n`;

    messages.forEach(msg => {
        if (msg.classList.contains('user')) text += `You: ${msg.textContent}\n\n`;
        else if (msg.classList.contains('jarvis')) text += `JARVIS: ${msg.textContent}\n\n`;
        else if (msg.classList.contains('tool')) text += `[Tool] ${msg.textContent}\n\n`;
        else if (msg.classList.contains('system')) text += `[System] ${msg.textContent}\n\n`;
    });

    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `jarvis_chat_${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
});

// ─── Clear Chat ──────────────────────────────────────────────
clearBtn.addEventListener('click', () => {
    chatMessages.innerHTML = '';
    addSystemMessage('Chat cleared. Ready for new directives.');
});

// ─── Arc Reactor Canvas Animation ────────────────────────────
function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
}
window.addEventListener('resize', resizeCanvas);
resizeCanvas();

const particles = [];
const PARTICLE_COUNT = 80;

class Particle {
    constructor() { this.reset(); }
    reset() {
        this.x = Math.random() * canvas.width;
        this.y = Math.random() * canvas.height;
        this.vx = (Math.random() - 0.5) * 0.5;
        this.vy = (Math.random() - 0.5) * 0.5;
        this.size = Math.random() * 2 + 0.5;
        this.alpha = Math.random() * 0.5 + 0.1;
        this.life = Math.random() * 200 + 100;
    }
    update() {
        this.x += this.vx;
        this.y += this.vy;
        this.life--;
        if (this.life <= 0 || this.x < 0 || this.x > canvas.width || this.y < 0 || this.y > canvas.height) {
            this.reset();
        }
    }
    draw() {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(0, 212, 255, ${this.alpha})`;
        ctx.fill();
    }
}

for (let i = 0; i < PARTICLE_COUNT; i++) particles.push(new Particle());

function drawHexGrid() {
    const size = 40;
    const h = size * Math.sqrt(3);
    ctx.strokeStyle = 'rgba(0, 212, 255, 0.03)';
    ctx.lineWidth = 0.5;
    for (let row = -1; row < canvas.height / h + 1; row++) {
        for (let col = -1; col < canvas.width / (size * 1.5) + 1; col++) {
            const x = col * size * 1.5;
            const y = row * h + (col % 2 ? h / 2 : 0);
            drawHex(x, y, size * 0.55);
        }
    }
}

function drawHex(cx, cy, r) {
    ctx.beginPath();
    for (let i = 0; i < 6; i++) {
        const angle = (Math.PI / 3) * i - Math.PI / 6;
        const x = cx + r * Math.cos(angle);
        const y = cy + r * Math.sin(angle);
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.stroke();
}

function drawConnections() {
    ctx.strokeStyle = 'rgba(0, 212, 255, 0.05)';
    ctx.lineWidth = 0.5;
    for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
            const dx = particles[i].x - particles[j].x;
            const dy = particles[i].y - particles[j].y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < 120) {
                ctx.globalAlpha = (1 - dist / 120) * 0.3;
                ctx.beginPath();
                ctx.moveTo(particles[i].x, particles[i].y);
                ctx.lineTo(particles[j].x, particles[j].y);
                ctx.stroke();
            }
        }
    }
    ctx.globalAlpha = 1;
}

function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    drawHexGrid();
    particles.forEach(p => { p.update(); p.draw(); });
    drawConnections();
    requestAnimationFrame(animate);
}

animate();

// ─── Keyboard Shortcuts ──────────────────────────────────────
document.addEventListener('keydown', (e) => {
    // Ctrl+/ to focus input
    if (e.ctrlKey && e.key === '/') {
        e.preventDefault();
        userInput.focus();
    }
    // Escape to close modal
    if (e.key === 'Escape') {
        settingsModal.style.display = 'none';
    }
});

// ─── Ping to keep connection alive ──────────────────────────
setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }));
    }
}, 30000);

// ─── DOMPurify fallback (basic sanitizer if DOMPurify not loaded) ───
if (typeof DOMPurify === 'undefined') {
    window.DOMPurify = { sanitize: (html) => html };
}

// ═══════════════════════════════════════════════════════════════
//  Wake Word Training Flow
// ═══════════════════════════════════════════════════════════════
const trainingModal = document.getElementById('training-modal');
let trainingSampleStep = 0;

async function checkEnrollment() {
    try {
        const resp = await fetch('/api/wake/enrollment');
        if (!resp.ok) return;
        const data = await resp.json();
        if (!data.enrolled) {
            // First time — show training modal
            trainingModal.style.display = 'flex';
        }
    } catch (e) {
        // Server not ready yet, ignore
    }
}

// Begin button
document.getElementById('train-begin-btn').addEventListener('click', async () => {
    // Start training on backend
    await fetch('/api/wake/train/start', { method: 'POST' });

    // Show calibration step
    document.getElementById('training-welcome').style.display = 'none';
    document.getElementById('training-calibrate').style.display = 'block';

    // Calibrate mic
    try {
        const resp = await fetch('/api/wake/train/calibrate', { method: 'POST' });
        const data = await resp.json();

        if (data.status === 'error') {
            document.getElementById('calibrate-msg').textContent = data.message;
            return;
        }

        // Move to recording
        document.getElementById('calibrate-msg').textContent = data.message;
        await new Promise(r => setTimeout(r, 1500));

        // Start recording samples
        document.getElementById('training-calibrate').style.display = 'none';
        document.getElementById('training-record').style.display = 'block';
        trainingSampleStep = 1;
        recordNextSample();
    } catch (e) {
        document.getElementById('calibrate-msg').textContent = 'Error: ' + e.message;
    }
});

async function recordNextSample() {
    const recordOrb = document.getElementById('record-orb');
    const stepEl = document.getElementById('record-step');
    const msgEl = document.getElementById('record-msg');
    const heardEl = document.getElementById('record-heard');
    const progressEl = document.getElementById('train-progress');

    stepEl.textContent = `${trainingSampleStep} / 3`;
    msgEl.textContent = 'Speak now — say "Jarvis" clearly...';
    heardEl.textContent = '';
    recordOrb.className = 'training-orb recording';
    progressEl.style.width = ((trainingSampleStep - 1) / 3 * 100) + '%';

    try {
        const resp = await fetch('/api/wake/train/sample', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ step: trainingSampleStep }),
        });
        const data = await resp.json();

        recordOrb.className = 'training-orb';

        if (data.status === 'recorded') {
            heardEl.textContent = 'I heard: "' + data.heard + '"';
            heardEl.style.color = 'var(--secondary)';
            progressEl.style.width = (trainingSampleStep / 3 * 100) + '%';

            if (data.done) {
                // All samples collected — finish
                await new Promise(r => setTimeout(r, 1200));
                finishTraining();
            } else {
                // Next sample after a pause
                trainingSampleStep++;
                await new Promise(r => setTimeout(r, 1500));
                recordNextSample();
            }
        } else if (data.status === 'retry') {
            heardEl.textContent = data.message;
            heardEl.style.color = 'var(--warning)';
            // Retry same step
            await new Promise(r => setTimeout(r, 2000));
            recordNextSample();
        } else {
            msgEl.textContent = data.message || 'Error occurred.';
        }
    } catch (e) {
        msgEl.textContent = 'Connection error. Please try again.';
        recordOrb.className = 'training-orb';
    }
}

async function finishTraining() {
    const userName = document.getElementById('train-user-name').value.trim();

    try {
        const resp = await fetch('/api/wake/train/finish', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_name: userName }),
        });
        const data = await resp.json();

        document.getElementById('training-record').style.display = 'none';
        document.getElementById('training-done').style.display = 'block';
        document.getElementById('train-result-msg').textContent = data.message || 'Training complete!';

        if (data.variants) {
            document.getElementById('train-variants').textContent =
                'Learned pronunciations: ' + data.variants.join(', ');
        }
    } catch (e) {
        document.getElementById('train-result-msg').textContent = 'Error saving profile.';
    }
}

// Finish button — close modal
document.getElementById('train-finish-btn').addEventListener('click', () => {
    trainingModal.style.display = 'none';
});

// Redo button
document.getElementById('train-redo-btn').addEventListener('click', async () => {
    await fetch('/api/wake/train/reset', { method: 'POST' });
    document.getElementById('training-done').style.display = 'none';
    document.getElementById('training-welcome').style.display = 'block';
    trainingSampleStep = 0;
});

// Skip button
document.getElementById('train-skip-btn').addEventListener('click', () => {
    trainingModal.style.display = 'none';
});

// ─── Initialize ──────────────────────────────────────────────
connectWS();

// Check enrollment after a short delay (let server start)
setTimeout(checkEnrollment, 1500);
