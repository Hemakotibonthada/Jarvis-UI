"""
J.A.R.V.I.S. API Server — FastAPI + WebSocket for real-time communication.
"""

import json
import asyncio
import base64
from datetime import datetime
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import config
from core.brain import JarvisBrain
from core.voice import VoiceEngine

# ── Module imports ────────────────────────────────────────────
from modules.system_control import (
    system_info, open_application, close_application,
    list_running_processes, execute_command, set_volume,
    screenshot, clipboard_read, clipboard_write, type_text, hotkey,
    system_power, manage_window, wifi_control, bluetooth_control,
    manage_service, list_startup_programs, list_installed_programs,
    set_brightness, get_live_stats, run_script,
)
from modules.file_manager import (
    create_file, read_file, list_directory, delete_file,
    move_file, copy_file,
)
from modules.whatsapp import send_whatsapp
from modules.esp32 import esp32
from modules.image_gen import generate_image
from modules.code_gen import generate_code
from modules.web_search import web_search, get_weather
from modules.automation import scheduler
from modules.email_manager import send_email, read_emails, count_unread_emails
from modules.git_ops import git_operation
from modules.vision import (
    analyze_image, analyze_screenshot, read_pdf, summarize_pdf,
    generate_qr_code, ocr_image,
)
from modules.media import (
    youtube_search, play_youtube, control_media,
    spotify_search, open_url,
)
from modules.utilities import (
    translate_text, calculate, get_news, convert_units,
    network_scan, ping_host, get_datetime_info, fetch_url_content,
    create_zip, extract_zip, find_files,
)
from modules.smart_home import smart_home
from modules.database import database_query, db_manager
from modules.screen_recorder import recording_control, transcribe_audio
from modules.task_manager import task_manager
from modules.notes import notes_manager
from modules.network_tools import network_tool
from modules.clipboard_history import clipboard_history
from modules.wallpaper import wallpaper_control, download_and_set_wallpaper
from modules.personality import personality
from core.logger import get_logger, activity_log, LoggerFactory
from core.event_system import event_bus, Events
from core.plugin_manager import plugin_manager
from modules.text_processing import text_process
from modules.docker_manager import docker_operation
from modules.system_monitor import system_monitor
from modules.window_automation import window_operation
from modules.backup import backup_manager
from modules.finance import finance_operation
from modules.process_manager import process_operation
from modules.security_tools import security_tool
from modules.calendar_manager import calendar_manager
from modules.workflow_engine import workflow_engine
from modules.health_tracker import health_tracker
from modules.project_scaffold import scaffolder
from modules.ssh_manager import ssh_manager
from modules.system_optimizer import system_optimizer
from modules.notification_hub import notification_hub
from modules.data_visualization import chart_manager
from modules.home_inventory import inventory_manager
from core.cache import cache_operation
from modules.conversation_analyzer import conversation_analyzer
from modules.knowledge_base import knowledge_base
from modules.browser_automation import browser_operation
from modules.routine_engine import routine_manager
from modules.rss_reader import rss_reader
from modules.snippet_manager import snippet_manager
from modules.api_tester import api_tester
from modules.app_launcher import smart_launcher
from modules.learning import learning_manager
from modules.data_pipeline import data_pipeline
from modules.contact_manager import contact_manager
from modules.world_clock import timezone_operation
from modules.bookmark_manager import bookmark_manager
from modules.pomodoro import pomodoro_timer
from modules.expense_tracker import expense_tracker
from modules.journal import journal_manager
from modules.password_vault import password_vault
from modules.math_science import math_science_operation
from modules.color_tools import color_operation as color_tool_operation
from modules.data_generator import datagen_operation
from modules.live_vision import live_vision
from modules.streaming import streaming_processor
from modules.ollama_llm import list_ollama_models
from modules.gmail_agent import gmail_operation
from modules.activity_tracker import activity_tracker

LoggerFactory.initialize()
log = get_logger("server")

# ─── App Setup ────────────────────────────────────────────────
app = FastAPI(title="J.A.R.V.I.S.", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (UI)
app.mount("/static", StaticFiles(directory="ui"), name="static")


@app.on_event("startup")
async def on_startup():
    """Auto-start wake word listener and activity tracking."""
    try:
        result = start_wake_listener()
        log.info(f"Auto-start wake listener: {result}")
    except Exception as e:
        log.warning(f"Could not auto-start wake listener: {e}")
    try:
        result = activity_tracker.start_tracking(60)
        log.info(f"Auto-start activity tracking: {result}")
    except Exception as e:
        log.warning(f"Could not auto-start activity tracking: {e}")


# ─── Core Components ─────────────────────────────────────────
brain = JarvisBrain()
voice = VoiceEngine()
connected_clients: Set[WebSocket] = set()

# ─── Register Tool Handlers ──────────────────────────────────
# System
brain.register_tool("system_info", system_info)
brain.register_tool("open_application", open_application)
brain.register_tool("close_application", close_application)
brain.register_tool("list_running_processes", list_running_processes)
brain.register_tool("execute_command", execute_command)
brain.register_tool("set_volume", set_volume)
brain.register_tool("screenshot", screenshot)
brain.register_tool("set_brightness", set_brightness)
brain.register_tool("system_power", system_power)
brain.register_tool("manage_window", manage_window)
brain.register_tool("wifi_control", wifi_control)
brain.register_tool("bluetooth_control", bluetooth_control)
brain.register_tool("manage_service", manage_service)
brain.register_tool("list_startup_programs", list_startup_programs)
brain.register_tool("list_installed_programs", list_installed_programs)
brain.register_tool("run_script", run_script)

# Files
brain.register_tool("create_file", create_file)
brain.register_tool("read_file", read_file)
brain.register_tool("list_directory", list_directory)
brain.register_tool("delete_file", delete_file)
brain.register_tool("move_file", move_file)
brain.register_tool("copy_file", copy_file)
brain.register_tool("find_files", find_files)
brain.register_tool("create_zip", create_zip)
brain.register_tool("extract_zip", extract_zip)

# Clipboard & Keyboard
brain.register_tool("clipboard_read", clipboard_read)
brain.register_tool("clipboard_write", clipboard_write)
brain.register_tool("type_text", type_text)
brain.register_tool("hotkey", hotkey)

# Communication
brain.register_tool("send_whatsapp", send_whatsapp)
brain.register_tool("send_email", send_email)
brain.register_tool("read_emails", read_emails)
brain.register_tool("count_unread_emails", count_unread_emails)

# AI Generation
brain.register_tool("generate_image", generate_image)
brain.register_tool("generate_code", generate_code)

# Vision & Documents
brain.register_tool("analyze_image", analyze_image)
brain.register_tool("analyze_screenshot", analyze_screenshot)
brain.register_tool("read_pdf", read_pdf)
brain.register_tool("summarize_pdf", summarize_pdf)
brain.register_tool("ocr_image", ocr_image)
brain.register_tool("generate_qr_code", generate_qr_code)

# IoT / ESP32
brain.register_tool("esp32_read_sensors", esp32.esp32_read_sensors)
brain.register_tool("esp32_control", esp32.esp32_control)
brain.register_tool("esp32_connect_serial", esp32.connect_serial)
brain.register_tool("esp32_list_ports", esp32.list_serial_ports)

# Web & Information
brain.register_tool("web_search", web_search)
brain.register_tool("get_weather", get_weather)
brain.register_tool("get_news", get_news)
brain.register_tool("fetch_url_content", fetch_url_content)
brain.register_tool("get_datetime_info", get_datetime_info)

# Media
brain.register_tool("play_youtube", play_youtube)
brain.register_tool("youtube_search", youtube_search)
brain.register_tool("control_media", control_media)
brain.register_tool("spotify_search", spotify_search)
brain.register_tool("open_url", open_url)

# Utilities
brain.register_tool("translate_text", translate_text)
brain.register_tool("calculate", calculate)
brain.register_tool("convert_units", convert_units)
brain.register_tool("network_scan", network_scan)
brain.register_tool("ping_host", ping_host)

# Git
brain.register_tool("git_operation", git_operation)

# Reminders
brain.register_tool("set_reminder", scheduler.set_reminder)
brain.register_tool("list_reminders", scheduler.list_reminders)

# Smart Home
brain.register_tool("smart_home_control", smart_home.smart_home_control)

# Database
brain.register_tool("database_query", database_query)

# Task Management
brain.register_tool("task_operation", task_manager.task_operation)

# Notes
brain.register_tool("note_operation", notes_manager.note_operation)

# Network Tools
brain.register_tool("network_tool", network_tool)

# Recording
brain.register_tool("recording_control", recording_control)
brain.register_tool("transcribe_audio", transcribe_audio)

# Wallpaper & Theme
brain.register_tool("wallpaper_control", wallpaper_control)
brain.register_tool("download_and_set_wallpaper", download_and_set_wallpaper)

# Clipboard History
brain.register_tool("clipboard_operation", clipboard_history.clipboard_operation)

# Personality & Fun
brain.register_tool("get_daily_briefing", personality.get_daily_briefing)
brain.register_tool("tell_joke", personality.get_joke)
brain.register_tool("fun_fact", personality.get_fun_fact)
brain.register_tool("motivational_quote", personality.get_motivational_quote)
brain.register_tool("get_activity_stats", activity_log.get_stats)

# Text Processing
brain.register_tool("text_process", text_process)

# Docker
brain.register_tool("docker_operation", docker_operation)

# System Report
brain.register_tool("system_report", system_monitor.get_full_report)

# Window Automation
brain.register_tool("window_operation", window_operation)

# Backup
brain.register_tool("backup_operation", backup_manager.backup_operation)

# Finance
brain.register_tool("finance_operation", finance_operation)

# Process Management
brain.register_tool("process_operation", process_operation)

# Security
brain.register_tool("security_tool", security_tool)

# Calendar
brain.register_tool("calendar_operation", calendar_manager.calendar_operation)

# Workflow Engine
brain.register_tool("workflow_operation", workflow_engine.workflow_operation)
workflow_engine.set_tool_handlers(brain.tool_handlers)

# Health Tracker
brain.register_tool("health_operation", health_tracker.health_operation)

# Project Scaffolder
brain.register_tool("scaffold_project", scaffolder.scaffold_project)
brain.register_tool("list_project_templates", scaffolder.list_templates)

# SSH Manager
brain.register_tool("ssh_operation", ssh_manager.ssh_operation)

# System Optimizer
brain.register_tool("optimizer_operation", system_optimizer.optimizer_operation)

# Notifications
brain.register_tool("notification_operation", notification_hub.notification_operation)

# Data Visualization
brain.register_tool("visualization_operation", chart_manager.visualization_operation)

# Home Inventory
brain.register_tool("inventory_operation", inventory_manager.inventory_operation)

# Cache
brain.register_tool("cache_operation", cache_operation)

# Conversation Analyzer
brain.register_tool("analyze_operation", conversation_analyzer.analyze_operation)

# Knowledge Base
brain.register_tool("knowledge_operation", knowledge_base.knowledge_operation)

# Browser Automation
brain.register_tool("browser_operation", browser_operation)

# Routine Engine
brain.register_tool("routine_operation", routine_manager.routine_operation)

# RSS Reader
brain.register_tool("rss_operation", rss_reader.rss_operation)

# Snippet Manager
brain.register_tool("snippet_operation", snippet_manager.snippet_operation)

# API Tester
brain.register_tool("api_test_operation", api_tester.api_test_operation)

# Smart Launcher
brain.register_tool("launcher_operation", smart_launcher.launcher_operation)

# Learning / Flashcards
brain.register_tool("learning_operation", learning_manager.learning_operation)

# Data Pipeline
brain.register_tool("pipeline_operation", data_pipeline.pipeline_operation)

# Contact Manager
brain.register_tool("contact_operation", contact_manager.contact_operation)

# World Clock / Timezones
brain.register_tool("timezone_operation", timezone_operation)

# Bookmark Manager
brain.register_tool("bookmark_operation", bookmark_manager.bookmark_operation)

# Pomodoro Timer
brain.register_tool("pomodoro_operation", pomodoro_timer.pomodoro_operation)
# Note: pomodoro_timer._on_notify is set below after on_reminder is defined

# Expense Tracker
brain.register_tool("expense_operation", expense_tracker.expense_operation)

# Journal
brain.register_tool("journal_operation", journal_manager.journal_operation)

# Password Vault
brain.register_tool("vault_operation", password_vault.vault_operation)

# Math & Science
brain.register_tool("math_science_operation", math_science_operation)

# Color Tools
brain.register_tool("color_operation", color_tool_operation)

# Data Generator
brain.register_tool("datagen_operation", datagen_operation)

# Live Vision
brain.register_tool("live_vision", live_vision.vision_operation)

# Streaming Processor
streaming_processor.set_brain(brain, None)  # broadcast set after definition

# Gmail
brain.register_tool("gmail_operation", gmail_operation)

# Activity Tracker
brain.register_tool("activity_operation", activity_tracker.activity_operation)

# Ollama
brain.register_tool("list_ollama_models", list_ollama_models)

# ── Final tool count ──────────────────────────────────────────
log.info(f"J.A.R.V.I.S. fully loaded with {len(brain.tool_handlers)} tools across {80}+ modules")
log.info("All systems operational. Ready to serve.")

# Start clipboard monitoring
clipboard_history.start_monitoring()

# Load plugins
plugin_manager.load_all()
for tool_name, handler in plugin_manager.get_tools().items():
    brain.register_tool(tool_name, handler)

log.info(f"Registered {len(brain.tool_handlers)} tools")


# ─── Reminder callback ───────────────────────────────────────
async def on_reminder(message: str):
    """When a reminder triggers, notify all connected clients."""
    payload = json.dumps({
        "type": "reminder",
        "message": f"⏰ Reminder: {message}",
    })
    for ws in connected_clients.copy():
        try:
            await ws.send_text(payload)
        except Exception:
            connected_clients.discard(ws)

    # Also speak it
    await voice.speak(f"Reminder: {message}")

scheduler.on_reminder = on_reminder
pomodoro_timer._on_notify = on_reminder


# ─── Broadcast ref for streaming ──────────────────────────────
# (broadcast is defined below, set ref after)
_streaming_broadcast_set = False


# ─── Wake Word Listener ──────────────────────────────────────
import threading

_wake_thread = None
_wake_listening = False


def _on_voice_command(text: str):
    """Called from background thread when a voice command is detected."""
    log.info(f"Voice command detected: {text}")
    # Schedule async processing on the event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(_process_voice_command(text), loop)
    except RuntimeError:
        pass


async def _process_voice_command(text: str):
    """Process a voice command through the brain and broadcast result."""
    # Notify all clients that a voice command was received
    await broadcast(json.dumps({
        "type": "voice_detected",
        "message": text,
    }))
    await broadcast(json.dumps({
        "type": "thinking",
        "message": "Processing voice command...",
    }))

    # Think
    reply = await brain.think(text, broadcast=broadcast)

    # Send response to all clients
    await broadcast(json.dumps({
        "type": "response",
        "message": reply,
    }))

    # Speak the response (skip if too long or is a help/list dump)
    speak_text = reply
    if len(reply) > 500:
        speak_text = reply[:400] + "... I've sent the full details to your screen."
    try:
        audio_bytes = await voice.speak(speak_text)
        if audio_bytes:
            audio_b64 = base64.b64encode(audio_bytes).decode()
            await broadcast(json.dumps({
                "type": "audio",
                "data": audio_b64,
                "format": "mp3",
            }))
    except Exception as e:
        log.error(f"TTS error: {e}")


def _on_wake_detected():
    """Called when wake word 'Jarvis' is heard."""
    log.info("Wake word detected! Listening for command...")
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(
                broadcast(json.dumps({"type": "wake_word", "message": "Listening..."})),
                loop
            )
    except RuntimeError:
        pass


def start_wake_listener():
    """Start the background wake word listener."""
    global _wake_thread, _wake_listening
    if _wake_listening:
        return "Wake word listener already running."

    _wake_listening = True
    voice._on_wake = _on_wake_detected

    def _listener_thread():
        global _wake_listening
        log.info(f"Wake word listener started (wake word: '{voice.wake_word}')")
        try:
            voice.listen_continuous(_on_voice_command, use_wake_word=True)
        except Exception as e:
            log.error(f"Wake listener error: {e}")
        finally:
            _wake_listening = False
            log.info("Wake word listener stopped")

    _wake_thread = threading.Thread(target=_listener_thread, daemon=True, name="jarvis-wake-listener")
    _wake_thread.start()
    return f"Wake word listener started. Say '{voice.wake_word}' to activate."


def stop_wake_listener():
    """Stop the background wake word listener."""
    global _wake_listening
    if not _wake_listening:
        return "Wake word listener not running."
    _wake_listening = False
    voice.stop_listening()
    return "Wake word listener stopped."


# ─── Broadcast helper ────────────────────────────────────────
async def broadcast(message: str):
    """Send a message to all connected WebSocket clients."""
    for ws in connected_clients.copy():
        try:
            await ws.send_text(message)
        except Exception:
            connected_clients.discard(ws)

# Set broadcast for streaming processor
streaming_processor._broadcast = broadcast


# ─── Routes ──────────────────────────────────────────────────
@app.get("/")
async def root():
    return FileResponse("ui/index.html")


@app.get("/dashboard")
async def dashboard():
    return FileResponse("ui/dashboard.html")


@app.get("/api/health")
async def health():
    return {"status": "online", "name": "J.A.R.V.I.S.", "time": datetime.now().isoformat(),
            "wake_word_active": _wake_listening, "wake_word": voice.wake_word}


@app.post("/api/wake/start")
async def api_wake_start():
    """Start the wake word listener (microphone)."""
    result = start_wake_listener()
    return {"result": result, "active": _wake_listening}


@app.post("/api/wake/stop")
async def api_wake_stop():
    """Stop the wake word listener."""
    result = stop_wake_listener()
    return {"result": result, "active": _wake_listening}


@app.get("/api/wake/status")
async def api_wake_status():
    """Get wake word listener status."""
    return {
        "active": _wake_listening,
        "wake_word": voice.wake_word,
        "use_wake_word": voice.use_wake_word,
        "enrolled": wake_trainer.is_enrolled,
    }


# ─── Language Switch ──────────────────────────────────────────
@app.post("/api/language")
async def api_set_language(data: dict):
    """Switch language: en (English) or te (Telugu)."""
    lang = data.get("language", "en")
    result = voice.set_language(lang)
    return {"result": result, "language": voice.get_language()}


@app.get("/api/language")
async def api_get_language():
    """Get current language settings."""
    return voice.get_language()


# ─── Wake Word Training / Enrollment ─────────────────────────
from core.voice_enrollment import wake_trainer

# Load voice profile at startup and apply to voice engine
voice.load_voice_profile()


@app.get("/api/wake/enrollment")
async def api_enrollment_status():
    """Check if wake word training has been completed."""
    return wake_trainer.get_status()


@app.post("/api/wake/train/start")
async def api_train_start():
    """Begin wake word training session."""
    result = wake_trainer.start_training()
    return result


@app.post("/api/wake/train/calibrate")
async def api_train_calibrate():
    """Calibrate microphone for ambient noise."""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, wake_trainer.calibrate_mic)
    return result


@app.post("/api/wake/train/sample")
async def api_train_sample(data: dict):
    """Record one pronunciation sample."""
    step = int(data.get("step", 1))
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, wake_trainer.record_sample, step)
    return result


@app.post("/api/wake/train/finish")
async def api_train_finish(data: dict):
    """Finalize training and save profile."""
    user_name = data.get("user_name", "")
    result = wake_trainer.finish_training(user_name)
    # Reload profile into voice engine
    voice.load_voice_profile()
    return result


@app.post("/api/wake/train/reset")
async def api_train_reset():
    """Reset voice profile for re-enrollment."""
    result = wake_trainer.reset_profile()
    voice.load_voice_profile()
    return result


@app.post("/api/chat")
async def chat(data: dict):
    """REST endpoint for text chat."""
    user_input = data.get("message", "")
    if not user_input:
        return JSONResponse({"error": "No message provided"}, status_code=400)

    reply = await brain.think(user_input, broadcast=broadcast)
    return {"response": reply}


@app.post("/api/tts")
async def tts(data: dict):
    """Generate TTS audio from text."""
    text = data.get("text", "")
    if not text:
        return JSONResponse({"error": "No text"}, status_code=400)

    audio_bytes = await voice.speak(text)
    audio_b64 = base64.b64encode(audio_bytes).decode()
    return {"audio": audio_b64, "format": "mp3"}


@app.get("/api/stats")
async def live_stats():
    """Real-time system stats for the UI."""
    return get_live_stats()


@app.get("/api/history")
async def get_conversation_history():
    """Get conversation history from persistent memory."""
    history = brain.persistent.get_history(50)
    return {"history": history}


@app.get("/api/memories")
async def get_memories():
    """Get stored facts and preferences."""
    return {
        "facts": brain.persistent.list_facts(),
        "preferences": brain.persistent.list_preferences(),
    }


@app.get("/api/voices")
async def available_voices():
    """List available TTS voices."""
    voices = await voice.list_voices()
    return {"voices": voices[:30], "current": voice.tts_voice}


@app.post("/api/voice/set")
async def set_voice(data: dict):
    """Change TTS voice."""
    v = data.get("voice", "")
    if v:
        voice.set_voice(v)
        return {"voice": v}
    return JSONResponse({"error": "No voice specified"}, status_code=400)


# ─── Extended REST API ────────────────────────────────────────
@app.get("/api/tasks")
async def api_tasks():
    """Get task dashboard."""
    return {"summary": task_manager.get_summary(), "today": task_manager.get_today()}


@app.get("/api/tasks/list")
async def api_task_list():
    """List all tasks."""
    return {"tasks": task_manager.list_tasks()}


@app.post("/api/tasks")
async def api_create_task(data: dict):
    """Create a task via REST."""
    result = task_manager.add_task(
        data.get("title", ""),
        data.get("description", ""),
        int(data.get("priority", 0)),
        data.get("due_date", ""),
        data.get("project", ""),
    )
    return {"result": result}


@app.get("/api/notes")
async def api_notes():
    """List notes."""
    return {"notes": notes_manager.list_notes()}


@app.post("/api/notes")
async def api_create_note(data: dict):
    """Create a note."""
    result = notes_manager.create_note(
        data.get("title", ""),
        data.get("content", ""),
        data.get("category", ""),
    )
    return {"result": result}


@app.get("/api/db/info")
async def api_db_info():
    """Database info."""
    return {"info": db_manager.get_db_info()}


@app.get("/api/plugins")
async def api_plugins():
    """List loaded plugins."""
    return {"plugins": plugin_manager.list_plugins()}


@app.get("/api/activity")
async def api_activity():
    """Get recent activity."""
    recent = activity_log.get_recent(30)
    stats = activity_log.get_stats()
    return {"recent": recent, "stats": stats}


@app.get("/api/events")
async def api_events():
    """Get event history."""
    return {"events": event_bus.get_history(limit=50)}


@app.get("/api/personality/briefing")
async def api_briefing():
    """Get daily briefing."""
    return {"briefing": personality.get_daily_briefing()}


@app.get("/api/system/full")
async def api_full_system():
    """Get comprehensive system info."""
    stats = get_live_stats()
    from modules.system_control import system_info as si
    return {"stats": stats, "info": si()}


@app.get("/api/tools")
async def api_list_tools():
    """List all registered tools."""
    tools = list(brain.tool_handlers.keys())
    return {"tools": tools, "count": len(tools)}


# ─── Vision API ───────────────────────────────────────────────
@app.post("/api/vision/see")
async def api_vision_see(data: dict):
    """Look at screen or camera and describe what's visible."""
    source = data.get("source", "screen")
    question = data.get("question", "Describe what you see in detail.")
    result = await live_vision.see(source, question)
    return {"result": result, "source": source}


@app.post("/api/vision/read")
async def api_vision_read():
    """Read text from the screen."""
    result = await live_vision.read_screen()
    return {"result": result}


@app.post("/api/vision/capture")
async def api_vision_capture(data: dict):
    """Capture screen or camera to file."""
    source = data.get("source", "screen")
    result = await live_vision.capture_and_save(source)
    return {"result": result}


@app.get("/api/vision/cameras")
async def api_vision_cameras():
    """List available cameras."""
    return {"cameras": live_vision.camera.list_cameras()}


# ─── Streaming API ────────────────────────────────────────────
@app.post("/api/stream/start")
async def api_stream_start():
    """Start streaming speech processing."""
    result = await streaming_processor.start_streaming()
    return {"result": result, "status": streaming_processor.get_status()}


@app.post("/api/stream/stop")
async def api_stream_stop():
    """Stop streaming."""
    result = streaming_processor.stop_streaming()
    return {"result": result}


@app.get("/api/stream/status")
async def api_stream_status():
    """Get streaming status."""
    return streaming_processor.get_status()


# ─── WebSocket ────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_clients.add(ws)

    # Welcome message (only if this is the first/only client)
    if len(connected_clients) <= 1:
        greeting = personality.get_greeting()
    else:
        greeting = "Connected to J.A.R.V.I.S."
    await ws.send_text(json.dumps({
        "type": "greeting",
        "message": greeting,
    }))

    try:
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                msg = {"type": "chat", "message": data}

            msg_type = msg.get("type", "chat")

            if msg_type == "chat":
                user_text = msg.get("message", "")
                if not user_text:
                    continue

                # Acknowledge
                await ws.send_text(json.dumps({
                    "type": "thinking",
                    "message": "Processing...",
                }))

                # Think and respond
                reply = await brain.think(user_text, broadcast=broadcast)

                await ws.send_text(json.dumps({
                    "type": "response",
                    "message": reply,
                }))

                # Generate TTS audio and send
                try:
                    audio_bytes = await voice.speak(reply)
                    if audio_bytes:
                        audio_b64 = base64.b64encode(audio_bytes).decode()
                        await ws.send_text(json.dumps({
                            "type": "audio",
                            "data": audio_b64,
                            "format": "mp3",
                        }))
                except Exception:
                    pass  # Audio is optional

            elif msg_type == "voice":
                # Voice input from browser
                text = msg.get("text", "")
                if text:
                    await ws.send_text(json.dumps({
                        "type": "thinking",
                        "message": "Processing voice command...",
                    }))
                    reply = await brain.think(text, broadcast=broadcast)
                    await ws.send_text(json.dumps({
                        "type": "response",
                        "message": reply,
                    }))
                    try:
                        audio_bytes = await voice.speak(reply)
                        if audio_bytes:
                            await ws.send_text(json.dumps({
                                "type": "audio",
                                "data": base64.b64encode(audio_bytes).decode(),
                                "format": "mp3",
                            }))
                    except Exception:
                        pass

            elif msg_type == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect:
        connected_clients.discard(ws)
    except Exception:
        connected_clients.discard(ws)
