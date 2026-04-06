import os
import platform
from pathlib import Path

# ─── .env support ─────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ─── Base Paths ───────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
GENERATED_DIR = DATA_DIR / "generated"
LOGS_DIR = DATA_DIR / "logs"
MEMORY_DIR = DATA_DIR / "memory"
HISTORY_DIR = DATA_DIR / "history"

for d in [DATA_DIR, GENERATED_DIR, LOGS_DIR, MEMORY_DIR, HISTORY_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ─── OpenAI / LLM ────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_TTS_MODEL = "tts-1-hd"
OPENAI_TTS_VOICE = "onyx"  # alloy, echo, fable, onyx, nova, shimmer
OPENAI_IMAGE_MODEL = "dall-e-3"
OPENAI_VISION_MODEL = "gpt-4o"  # For image analysis

# ─── Voice ────────────────────────────────────────────────────
EDGE_TTS_VOICE = "en-US-GuyNeural"  # Human-like male voice
EDGE_TTS_VOICE_TELUGU = "te-IN-MohanNeural"  # Telugu male voice
WAKE_WORD = "jarvis"
SILENCE_TIMEOUT = 2  # seconds of silence before processing
USE_WAKE_WORD = True  # Enable wake word detection
LANGUAGE = os.getenv("JARVIS_LANG", "en")  # "en" or "te" (Telugu)
STT_LANGUAGE = os.getenv("JARVIS_STT_LANG", "en-US")  # Google STT language code

# ─── ESP32 / IoT ─────────────────────────────────────────────
ESP32_SERIAL_PORT = os.getenv("ESP32_PORT", "COM3")
ESP32_BAUD_RATE = 115200
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC_PREFIX = "jarvis/esp32"

# ─── Email ────────────────────────────────────────────────────
EMAIL_ADDRESS = os.getenv("JARVIS_EMAIL", "")
EMAIL_PASSWORD = os.getenv("JARVIS_EMAIL_PASSWORD", "")
EMAIL_SMTP_SERVER = os.getenv("JARVIS_SMTP", "smtp.gmail.com")
EMAIL_SMTP_PORT = int(os.getenv("JARVIS_SMTP_PORT", "587"))
EMAIL_IMAP_SERVER = os.getenv("JARVIS_IMAP", "imap.gmail.com")

# ─── WhatsApp ─────────────────────────────────────────────────
WHATSAPP_WAIT_TIME = 15  # seconds to wait for WhatsApp Web to load

# ─── Spotify ──────────────────────────────────────────────────
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")

# ─── News ─────────────────────────────────────────────────────
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

# ─── Server ───────────────────────────────────────────────────
API_HOST = "127.0.0.1"
API_PORT = int(os.getenv("JARVIS_PORT", "8765"))
WS_URL = f"ws://{API_HOST}:{API_PORT}/ws"
API_TOKEN = os.getenv("JARVIS_API_TOKEN", "")  # Optional auth token

# ─── Platform ────────────────────────────────────────────────
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"
IS_MAC = platform.system() == "Darwin"
SYSTEM_DRIVE = os.getenv("SystemDrive", "C:") + "\\" if IS_WINDOWS else "/"

# ─── System ───────────────────────────────────────────────────
SYSTEM_PROMPT = """You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), an advanced AI assistant 
created to help manage systems, automate tasks, and assist with anything the user needs.

You have access to the following capabilities:
- System control: Open/close apps, manage files, read system info, control processes, window management
- Power management: Shutdown, restart, sleep, lock the computer  
- WhatsApp messaging: Send messages to contacts
- Email: Read, send, and manage emails
- ESP32/IoT: Read sensors (temperature, humidity), control connected devices
- Code generation: Write code in any language, run scripts
- Image generation: Create images from descriptions using DALL-E
- Image/Screen analysis: Analyze screenshots and images with vision AI
- File management: Create, read, modify, delete, search, zip files and folders
- Web search, news headlines, and weather
- YouTube search and music control  
- Translation, math calculations, unit conversion
- QR code generation
- PDF reading and summarization
- Git operations: status, commit, push, pull, branch management
- Reminders, timers, and scheduled tasks
- Clipboard management, keyboard automation
- Network scanning and diagnostics
- System service management

Personality: You are professional, witty, and efficient — like the AI from Iron Man.
Always be helpful and proactive. Think step by step before acting.
When controlling the system, confirm dangerous operations before executing.
Respond concisely but include personality. Use sir/ma'am when appropriate.
When showing information, format it clearly. Use markdown formatting for code, lists, and tables."""
