# J.A.R.V.I.S. — Just A Rather Very Intelligent System v2.0

An AI-powered personal assistant with 60+ tools, system control, voice interaction, IoT integration, and an Iron Man-style animated HUD.

## Features (60+ Tools)

| Category | Features |
|----------|----------|
| **AI Brain** | GPT-4o reasoning, function calling chains, persistent memory, fact storage |
| **Voice** | Human-like TTS (Edge-TTS), STT, wake word detection ("Jarvis") |
| **System Control** | Open/close apps, manage processes, screenshots, volume, brightness |
| **Power Management** | Shutdown, restart, sleep, lock, hibernate, logoff |
| **Window Management** | Minimize, maximize, snap, virtual desktops, task view |
| **WiFi/Bluetooth** | Scan, connect, disconnect, status |
| **WhatsApp** | Send messages via WhatsApp Web |
| **Email** | Send and read emails via SMTP/IMAP |
| **ESP32/IoT** | Read temp/humidity, control LEDs/relays via Serial or MQTT |
| **Image Generation** | DALL-E 3 HD image creation |
| **Image Analysis** | GPT-4o Vision for image/screenshot analysis |
| **Code Generation** | Generate code in any language |
| **File Management** | Create, read, move, copy, delete, search, zip files |
| **PDF & OCR** | Read PDFs, summarize with AI, OCR text extraction |
| **QR Codes** | Generate QR code images |
| **Git Operations** | Status, commit, push, pull, branch, clone, stash |
| **Web Search** | DuckDuckGo search, webpage content extraction |
| **Weather** | Real-time weather from wttr.in |
| **News** | Google News RSS headlines |
| **Media Control** | Play/pause/next, YouTube search, Spotify |
| **Translation** | 50+ language translations |
| **Calculator** | Safe math evaluation (sqrt, sin, log, etc.) |
| **Unit Conversion** | Temp, distance, weight, speed, data |
| **Network** | Interface scan, ping, diagnostics |
| **Automation** | Reminders, scheduled tasks |
| **Memory** | Persistent facts, user preferences, conversation history |
| **Clipboard** | Read/write clipboard, keyboard simulation |
| **Services** | Start/stop/restart system services |
| **Animated UI** | Iron Man HUD with particles, hex grid, orb, markdown chat |

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure
```bash
cp .env.example .env
# Edit .env with your OPENAI_API_KEY
```

Or set directly:
```powershell
$env:OPENAI_API_KEY = "sk-your-key-here"
```

### 3. Run
```bash
python main.py
```

### CLI Options
```
python main.py --port 9000      # Custom port
python main.py --no-browser     # Don't auto-open browser
python main.py --debug          # Debug mode with hot reload
python main.py --voice en-US-JennyNeural  # Different voice
```

Opens at **http://127.0.0.1:8765** with the animated HUD interface.

## ESP32 Setup

1. Flash `esp32/jarvis_esp32.ino` to your ESP32 board using Arduino IDE
2. Libraries needed: DHT sensor library, ArduinoJson
3. Connect DHT22 sensor to GPIO 4
4. Set the COM port: `$env:ESP32_PORT = "COM3"`

### MQTT (Optional)
```
MQTT_BROKER=192.168.1.100
MQTT_PORT=1883
```

## Architecture

```
Jarvis/
├── main.py                    # Entry point with CLI args
├── config.py                  # All configuration + .env support
├── .env.example               # Environment template
├── requirements.txt
├── core/
│   ├── brain.py               # AI reasoning + 60 tool definitions
│   ├── voice.py               # TTS + STT + wake word detection
│   └── memory.py              # Conversation + persistent memory
├── modules/
│   ├── system_control.py      # OS, apps, power, windows, WiFi, BT, services
│   ├── file_manager.py        # File CRUD + move/copy
│   ├── whatsapp.py            # WhatsApp messaging
│   ├── email_manager.py       # SMTP/IMAP email
│   ├── esp32.py               # Serial + MQTT IoT
│   ├── image_gen.py           # DALL-E image generation
│   ├── code_gen.py            # AI code generation
│   ├── vision.py              # GPT-4o vision, PDF, OCR, QR codes
│   ├── media.py               # YouTube, Spotify, media control
│   ├── git_ops.py             # Git operations
│   ├── web_search.py          # Web search + weather
│   ├── utilities.py           # Translation, math, news, network, zip
│   └── automation.py          # Reminders & scheduling
├── api/
│   └── server.py              # FastAPI + WebSocket + REST APIs
├── ui/
│   ├── index.html             # HUD with settings, quick actions
│   ├── styles.css             # Iron Man CSS + markdown + modals
│   └── script.js              # Real stats, markdown, export, notifications
├── esp32/
│   └── jarvis_esp32.ino       # Arduino firmware
└── data/
    ├── generated/             # Screenshots, images, QR codes
    ├── memory/                # Persistent facts & preferences
    ├── history/               # Conversation logs
    └── logs/
```

## Voice Commands (Examples)

- "Open Chrome" / "Close Notepad"
- "What's the system status?"
- "Lock the computer" / "Set brightness to 50%"
- "Snap this window to the left"
- "Send a WhatsApp message to +1234567890 saying hello"
- "Send an email to john@example.com about the meeting"
- "Check my emails"
- "Read the temperature from ESP32" / "Turn on the LED"
- "Generate an image of a futuristic city"
- "Analyze the screenshot - what's on my screen?"
- "Create a Python script that sorts files by date"
- "Read this PDF and summarize it"
- "Generate a QR code for my website"
- "Git status" / "Commit with message 'fix bug'"
- "Translate 'hello world' to Japanese"
- "What's sqrt(144) + 2^3?"
- "Convert 100 km to miles"
- "Play lo-fi on YouTube"
- "What's the latest tech news?"
- "Set a reminder in 30 minutes to take a break"
- "Remember that my favorite color is blue"
- "What did I tell you about my favorite color?"
- "Ping google.com" / "Show network info"
- "List WiFi networks"
