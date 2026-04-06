"""
J.A.R.V.I.S. Brain — AI reasoning engine powered by OpenAI.
Handles thinking, planning, tool selection, and conversation.
"""

import json
import re
import asyncio
from datetime import datetime
from core.memory import ConversationMemory, PersistentMemory
import config

# Try to create OpenAI client — may fail if key is empty/invalid
_openai_available = False
_openai_failed_permanently = False
client = None
try:
    if config.OPENAI_API_KEY and len(config.OPENAI_API_KEY) > 10:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        _openai_available = True
except Exception:
    pass

# ─── Tool definitions for function calling ────────────────────
# ─── Helper to define tools concisely ─────────────────────────
def _tool(name, desc, params=None, required=None):
    fn = {"name": name, "description": desc, "parameters": {"type": "object", "properties": params or {}, "required": required or []}}
    return {"type": "function", "function": fn}

def _p(desc, type_="string", enum=None, default=None):
    d = {"type": type_, "description": desc}
    if enum: d["enum"] = enum
    if default is not None: d["default"] = default
    return d

TOOLS = [
    # ── System ────────────────────────────────────────────
    _tool("system_info", "Get system information: CPU, RAM, disk, battery, network, OS details"),
    _tool("open_application", "Open an application by name", {"app_name": _p("Name of the application")}, ["app_name"]),
    _tool("close_application", "Close a running application by name", {"app_name": _p("Name of the application")}, ["app_name"]),
    _tool("list_running_processes", "List top running processes by memory usage"),
    _tool("execute_command", "Execute a shell command. Use with caution.", {"command": _p("Shell command to execute")}, ["command"]),
    _tool("set_volume", "Set the system volume level", {"level": _p("Volume 0-100", "integer")}, ["level"]),
    _tool("screenshot", "Take a screenshot of the current screen"),
    _tool("set_brightness", "Set screen brightness", {"level": _p("Brightness 0-100", "integer")}, ["level"]),
    _tool("system_power", "Power management: shutdown, restart, sleep, lock, hibernate, logoff, cancel_shutdown", {"action": _p("Power action", enum=["shutdown", "restart", "sleep", "lock", "hibernate", "logoff", "cancel_shutdown"])}, ["action"]),
    _tool("manage_window", "Window management actions", {"action": _p("Action to perform", enum=["minimize", "maximize", "close", "snap_left", "snap_right", "minimize_all", "show_desktop", "switch", "task_view", "new_desktop", "close_desktop", "next_desktop", "prev_desktop"]), "window_title": _p("Optional window title")}, ["action"]),
    _tool("wifi_control", "WiFi management: list, connect, disconnect, status", {"action": _p("WiFi action", enum=["list", "connect", "disconnect", "status"]), "network_name": _p("WiFi network name"), "password": _p("WiFi password")}, ["action"]),
    _tool("bluetooth_control", "Bluetooth control: on, off, status", {"action": _p("Action", enum=["on", "off", "status"])}, ["action"]),
    _tool("manage_service", "Manage system services", {"action": _p("Action", enum=["start", "stop", "restart", "status"]), "service_name": _p("Service name")}, ["action", "service_name"]),
    _tool("list_startup_programs", "List programs that run at startup"),
    _tool("list_installed_programs", "List all installed programs"),
    _tool("run_script", "Run a Python/JS/bash/PowerShell script file", {"file_path": _p("Path to the script file")}, ["file_path"]),

    # ── Files ─────────────────────────────────────────────
    _tool("create_file", "Create a file with content", {"file_path": _p("File path"), "content": _p("File content")}, ["file_path", "content"]),
    _tool("read_file", "Read a file's contents", {"file_path": _p("File path")}, ["file_path"]),
    _tool("list_directory", "List directory contents", {"dir_path": _p("Directory path"), "recursive": _p("Recursive listing", "boolean")}, ["dir_path"]),
    _tool("delete_file", "Delete a file or directory", {"path": _p("Path to delete")}, ["path"]),
    _tool("move_file", "Move/rename a file or directory", {"src": _p("Source path"), "dst": _p("Destination path")}, ["src", "dst"]),
    _tool("copy_file", "Copy a file or directory", {"src": _p("Source path"), "dst": _p("Destination path")}, ["src", "dst"]),
    _tool("find_files", "Search for files by name pattern", {"directory": _p("Directory to search"), "pattern": _p("Glob pattern like *.py, *.txt")}, ["directory", "pattern"]),
    _tool("create_zip", "Create a zip archive from files", {"paths": {"type": "array", "items": {"type": "string"}, "description": "List of file/folder paths"}, "output_path": _p("Output zip file path")}, ["paths", "output_path"]),
    _tool("extract_zip", "Extract a zip archive", {"zip_path": _p("Path to zip file"), "dest": _p("Destination directory")}, ["zip_path"]),

    # ── Clipboard & Keyboard ──────────────────────────────
    _tool("clipboard_read", "Read clipboard content"),
    _tool("clipboard_write", "Write text to clipboard", {"text": _p("Text to copy")}, ["text"]),
    _tool("type_text", "Type text using keyboard simulation", {"text": _p("Text to type")}, ["text"]),
    _tool("hotkey", "Press a keyboard hotkey combination", {"keys": _p("Keys e.g. 'ctrl+shift+s'")}, ["keys"]),

    # ── Communication ─────────────────────────────────────
    _tool("send_whatsapp", "Send a WhatsApp message", {"to": _p("Phone with country code (+1234567890)"), "message": _p("Message text")}, ["to", "message"]),
    _tool("send_email", "Send an email", {"to": _p("Email address"), "subject": _p("Subject line"), "body": _p("Email body")}, ["to", "subject", "body"]),
    _tool("read_emails", "Read recent emails", {"count": _p("Number of emails", "integer"), "folder": _p("Mail folder", default="INBOX")}),
    _tool("count_unread_emails", "Count unread emails in inbox"),

    # ── AI Generation ─────────────────────────────────────
    _tool("generate_image", "Generate an image from a text description using DALL-E", {"prompt": _p("Image description"), "size": _p("Image size", enum=["1024x1024", "1024x1792", "1792x1024"])}, ["prompt"]),
    _tool("generate_code", "Generate code in any language and save to file", {"description": _p("What the code should do"), "language": _p("Programming language"), "file_path": _p("Where to save")}, ["description", "language", "file_path"]),

    # ── Vision & Documents ────────────────────────────────
    _tool("analyze_image", "Analyze an image using AI vision", {"image_path": _p("Path to the image"), "question": _p("Question about the image")}, ["image_path"]),
    _tool("analyze_screenshot", "Take a screenshot and analyze it with AI", {"question": _p("What to analyze on screen")}),
    _tool("read_pdf", "Read text from a PDF file", {"file_path": _p("Path to PDF"), "max_pages": _p("Max pages to read", "integer")}, ["file_path"]),
    _tool("summarize_pdf", "Read and summarize a PDF with AI", {"file_path": _p("Path to PDF")}, ["file_path"]),
    _tool("ocr_image", "Extract text from an image using OCR", {"image_path": _p("Path to the image")}, ["image_path"]),
    _tool("generate_qr_code", "Generate a QR code image", {"data": _p("Data to encode"), "file_name": _p("Output filename")}, ["data"]),

    # ── IoT / ESP32 ───────────────────────────────────────
    _tool("esp32_read_sensors", "Read temperature and humidity from ESP32 sensors"),
    _tool("esp32_control", "Send control command to ESP32 (LED_ON, LED_OFF, RELAY_ON, etc.)", {"command": _p("Command to send"), "params": {"type": "object", "description": "Additional parameters"}}, ["command"]),
    _tool("esp32_connect_serial", "Connect to ESP32 via serial port", {"port": _p("Serial port e.g. COM3"), "baud": _p("Baud rate", "integer")}),
    _tool("esp32_list_ports", "List available serial ports"),

    # ── Web & Information ─────────────────────────────────
    _tool("web_search", "Search the web for information", {"query": _p("Search query")}, ["query"]),
    _tool("get_weather", "Get weather for a location", {"location": _p("City or location")}, ["location"]),
    _tool("get_news", "Get news headlines on a topic", {"topic": _p("News topic"), "count": _p("Number of headlines", "integer")}, ["topic"]),
    _tool("fetch_url_content", "Fetch and extract text from a webpage", {"url": _p("URL to fetch")}, ["url"]),
    _tool("get_datetime_info", "Get current date, time, timezone info"),

    # ── Media & Entertainment ─────────────────────────────
    _tool("play_youtube", "Play a YouTube video by search query", {"query": _p("Search query")}, ["query"]),
    _tool("youtube_search", "Search YouTube and open results", {"query": _p("Search query")}, ["query"]),
    _tool("control_media", "Control media playback", {"action": _p("Action", enum=["play", "pause", "next", "previous", "volume_up", "volume_down", "mute", "stop"])}, ["action"]),
    _tool("spotify_search", "Search Spotify and open results", {"query": _p("Search query")}, ["query"]),
    _tool("open_url", "Open a URL in the browser", {"url": _p("URL to open")}, ["url"]),

    # ── Utilities ─────────────────────────────────────────
    _tool("translate_text", "Translate text between languages", {"text": _p("Text to translate"), "to_lang": _p("Target language code e.g. es, fr, de, ja"), "from_lang": _p("Source language code", default="auto")}, ["text", "to_lang"]),
    _tool("calculate", "Evaluate a math expression safely", {"expression": _p("Math expression e.g. 'sqrt(144) + 2**3'")}, ["expression"]),
    _tool("convert_units", "Convert between units", {"value": _p("Numeric value", "number"), "from_unit": _p("Source unit"), "to_unit": _p("Target unit")}, ["value", "from_unit", "to_unit"]),
    _tool("network_scan", "Get network info and interfaces"),
    _tool("ping_host", "Ping a host", {"host": _p("Hostname or IP")}, ["host"]),

    # ── Git ───────────────────────────────────────────────
    _tool("git_operation", "Git operations: status, log, diff, commit, push, pull, branch, checkout, clone, stash", {"operation": _p("Git operation", enum=["status", "log", "diff", "commit", "push", "pull", "branch", "checkout", "clone", "stash"]), "repo_path": _p("Repository path", default="."), "message": _p("Commit message"), "branch": _p("Branch name"), "url": _p("Clone URL"), "count": _p("Log count", "integer")}, ["operation"]),

    # ── Reminders & Scheduling ────────────────────────────
    _tool("set_reminder", "Set a timed reminder", {"message": _p("Reminder message"), "seconds": _p("Seconds from now", "integer")}, ["message", "seconds"]),
    _tool("list_reminders", "List all active reminders"),

    # ── Memory & Knowledge ────────────────────────────────
    _tool("remember", "Store a fact or piece of information for later", {"key": _p("Short key/name"), "value": _p("Information to remember")}, ["key", "value"]),
    _tool("recall", "Recall a previously stored fact", {"key": _p("Key to look up")}, ["key"]),
    _tool("list_memories", "List all stored facts and memories"),
    _tool("forget", "Forget a stored fact", {"key": _p("Key to forget")}, ["key"]),
    _tool("set_preference", "Set a user preference", {"key": _p("Preference name"), "value": _p("Preference value")}, ["key", "value"]),
    _tool("search_history", "Search past conversations", {"query": _p("Search query")}, ["query"]),

    # ── Smart Home ────────────────────────────────────────
    _tool("smart_home_control", "Control smart home devices via Home Assistant", {
        "action": _p("Action", enum=["status", "turn_on", "turn_off", "toggle", "set_light", "thermostat", "lock", "unlock", "find", "scene", "devices", "history"]),
        "device": _p("Entity ID or device name"),
        "value": _p("Value (e.g., temperature)"),
        "brightness": _p("Light brightness 0-255", "integer"),
        "color": _p("Light color name (red, blue, warm, etc.)"),
    }, ["action"]),

    # ── Database & Data ───────────────────────────────────
    _tool("database_query", "Store/retrieve structured data: contacts, bookmarks, key-value pairs, sensor data", {
        "operation": _p("Operation", enum=["set", "get", "delete", "list", "search", "info", "sql", "add_contact", "find_contact", "list_contacts", "add_bookmark", "find_bookmarks", "list_bookmarks", "log_sensor", "sensor_history", "sensor_stats"]),
        "key": _p("Key for key-value operations"),
        "value": _p("Value to store"),
        "category": _p("Category/group"),
        "query": _p("Search query or SQL"),
        "name": _p("Contact/bookmark name"),
        "phone": _p("Phone number"),
        "email": _p("Email address"),
        "title": _p("Bookmark title"),
        "url": _p("Bookmark URL"),
        "sensor": _p("Sensor name"),
        "unit": _p("Measurement unit"),
    }, ["operation"]),

    # ── Task Management ───────────────────────────────────
    _tool("task_operation", "Full task/project management with habits and time tracking", {
        "operation": _p("Operation", enum=["add", "list", "done", "start", "block", "delete", "get", "search", "overdue", "today", "summary", "projects", "create_project", "habits", "add_habit", "complete_habit", "start_timer", "stop_timer", "time_summary"]),
        "title": _p("Task or project title"),
        "description": _p("Task description"),
        "priority": _p("Priority 0-3 (0=normal, 3=critical)", "integer"),
        "due_date": _p("Due date YYYY-MM-DD"),
        "project": _p("Project name"),
        "task_id": _p("Task ID number", "integer"),
        "status": _p("Status filter"),
        "name": _p("Habit or project name"),
        "query": _p("Search query"),
        "tags": _p("Comma-separated tags"),
        "frequency": _p("Habit frequency: daily, weekly"),
        "days": _p("Number of days for summary", "integer"),
    }, ["operation"]),

    # ── Notes ─────────────────────────────────────────────
    _tool("note_operation", "Create, read, search, and manage persistent notes", {
        "operation": _p("Operation", enum=["create", "get", "update", "append", "delete", "list", "search", "pin", "categories", "export"]),
        "title": _p("Note title"),
        "content": _p("Note content"),
        "category": _p("Category"),
        "tags": _p("Tags"),
        "note_id": _p("Note ID", "integer"),
        "query": _p("Search query"),
        "text": _p("Text to append"),
        "file_path": _p("Export file path"),
    }, ["operation"]),

    # ── Network Tools ─────────────────────────────────────
    _tool("network_tool", "Advanced networking: port scan, DNS, traceroute, bandwidth, whois", {
        "operation": _p("Operation", enum=["port_scan", "quick_scan", "dns", "traceroute", "ip_info", "bandwidth", "arp", "whois", "usage", "connections"]),
        "target": _p("Target host/IP/domain"),
        "start_port": _p("Start port for scanning", "integer"),
        "end_port": _p("End port for scanning", "integer"),
    }, ["operation"]),

    # ── Recording ─────────────────────────────────────────
    _tool("recording_control", "Screen and audio recording control", {
        "action": _p("Action", enum=["start_screen", "stop_screen", "start_audio", "stop_audio", "status", "list"]),
        "name": _p("Output filename"),
        "fps": _p("Frames per second", "integer"),
        "duration": _p("Recording duration in seconds", "integer"),
    }, ["action"]),
    _tool("transcribe_audio", "Transcribe an audio file using AI", {"file_path": _p("Path to audio file")}, ["file_path"]),

    # ── Wallpaper & Theme ─────────────────────────────────
    _tool("wallpaper_control", "Change wallpaper and system theme", {
        "action": _p("Action", enum=["set", "current", "dark_mode", "light_mode", "accent"]),
        "path": _p("Image path for wallpaper"),
        "color": _p("Hex color for accent, e.g., #FF5500"),
        "enable": _p("Enable/disable", "boolean"),
    }, ["action"]),
    _tool("download_and_set_wallpaper", "Download a wallpaper from the web and set it", {"query": _p("Search term like 'mountains', 'space', 'city'")}, ["query"]),

    # ── Clipboard History ─────────────────────────────────
    _tool("clipboard_operation", "Manage clipboard history: view, search, restore past clips", {
        "operation": _p("Operation", enum=["history", "search", "get", "paste", "clear", "start", "stop"]),
        "query": _p("Search query"),
        "count": _p("Number of entries", "integer"),
        "index": _p("Entry index", "integer"),
    }, ["operation"]),

    # ── Personality & Fun ─────────────────────────────────
    _tool("get_daily_briefing", "Get a personalized daily briefing"),
    _tool("tell_joke", "Tell a programming/tech joke"),
    _tool("fun_fact", "Share a random fun fact"),
    _tool("motivational_quote", "Share a motivational quote"),
    _tool("get_activity_stats", "Get usage statistics and analytics"),

    # ── Text Processing ───────────────────────────────────
    _tool("text_process", "Advanced text processing: summarize, rephrase, proofread, extract entities, explain code, review code, generate tests, text stats, transformations, JSON/CSV conversion, regex, diff", {
        "operation": _p("Operation", enum=["summarize", "rephrase", "extract_entities", "proofread", "explain_code", "generate_tests", "review_code", "stats", "transform", "format_json", "json_to_csv", "csv_to_json", "regex_extract", "regex_replace", "diff"]),
        "text": _p("Input text"),
        "style": _p("Summary style: concise, detailed, bullet_points, eli5"),
        "tone": _p("Rephrase tone: professional, casual, formal, friendly"),
        "language": _p("Programming language for code operations"),
        "transform_type": _p("Transform type: uppercase, lowercase, title, reverse, sort_lines, slug, camel_case, snake_case"),
        "pattern": _p("Regex pattern"),
        "replacement": _p("Regex replacement string"),
    }, ["operation", "text"]),

    # ── Docker ────────────────────────────────────────────
    _tool("docker_operation", "Docker container management: ps, images, start, stop, restart, logs, inspect, stats, exec, pull, build, compose_up, compose_down, info, prune", {
        "operation": _p("Operation", enum=["ps", "images", "start", "stop", "restart", "remove", "logs", "inspect", "stats", "exec", "pull", "build", "compose_up", "compose_down", "info", "prune", "volumes", "networks"]),
        "container": _p("Container name or ID"),
        "image": _p("Image name"),
        "command": _p("Command to exec in container"),
        "path": _p("Path for build/compose"),
        "tag": _p("Image tag for build"),
        "tail": _p("Number of log lines", "integer"),
    }, ["operation"]),

    # ── System Report ─────────────────────────────────────
    _tool("system_report", "Generate a comprehensive system health report"),

    # ── Window Automation ──────────────────────────────────
    _tool("window_operation", "Advanced window management: list, find, focus, move, resize, minimize, maximize, close, arrange, opacity, always-on-top", {
        "operation": _p("Operation", enum=["list", "find", "focus", "move", "minimize", "maximize", "close", "arrange", "screen_info", "opacity", "always_on_top"]),
        "title": _p("Window title to search for"),
        "x": _p("X position", "integer"),
        "y": _p("Y position", "integer"),
        "width": _p("Window width", "integer"),
        "height": _p("Window height", "integer"),
        "layout": _p("Arrange layout: tile, cascade, side_by_side, stack"),
        "opacity": _p("Window opacity 0-255", "integer"),
    }, ["operation"]),

    # ── Backup ─────────────────────────────────────────────
    _tool("backup_operation", "Backup management: create, list, restore, delete, cleanup, checksum, compare directories", {
        "operation": _p("Operation", enum=["create", "list", "restore", "delete", "cleanup", "checksum", "compare"]),
        "source": _p("Source file/directory path"),
        "name": _p("Backup name"),
        "index": _p("Backup index for restore/delete", "integer"),
        "dest": _p("Restore destination path"),
        "path": _p("File path for checksum"),
        "algorithm": _p("Hash algorithm: md5, sha256"),
        "dir1": _p("First directory for comparison"),
        "dir2": _p("Second directory for comparison"),
        "compress": _p("Compress backup as zip", "boolean"),
    }, ["operation"]),

    # ── Finance & Crypto ─────────────────────────────────
    _tool("finance_operation", "Financial data: crypto prices, stock quotes, currency conversion, exchange rates", {
        "operation": _p("Operation", enum=["crypto_price", "crypto_list", "convert_currency", "exchange_rates", "stock"]),
        "symbol": _p("Crypto/stock symbol (e.g., bitcoin, BTC, AAPL, MSFT)"),
        "amount": _p("Amount to convert", "number"),
        "from_currency": _p("Source currency code e.g. USD"),
        "to_currency": _p("Target currency code e.g. EUR"),
        "base": _p("Base currency for exchange rates"),
        "limit": _p("Number of results", "integer"),
    }, ["operation"]),

    # ── Process Management ───────────────────────────────
    _tool("process_operation", "Advanced process management: kill, details, resource hogs, priority, port lookup, process tree, suspend, resume", {
        "operation": _p("Operation", enum=["kill", "details", "hogs", "priority", "port", "tree", "suspend", "resume"]),
        "target": _p("Process name or PID"),
        "force": _p("Force kill", "boolean"),
        "sort_by": _p("Sort: memory or cpu"),
        "priority": _p("Priority: low, normal, high, realtime"),
        "port": _p("Port number", "integer"),
        "pid": _p("Parent PID for tree", "integer"),
        "top": _p("Number of results", "integer"),
    }, ["operation"]),

    # ── Security ──────────────────────────────────────────
    _tool("security_tool", "Security tools: passwords, hashing, encryption, SSL checks, port audits, firewall, integrity", {
        "operation": _p("Operation", enum=["generate_password", "generate_passphrase", "check_password", "hash", "hash_file", "base64_encode", "base64_decode", "url_encode", "url_decode", "hex_encode", "hex_decode", "uuid", "token", "caesar", "rot13", "hmac", "port_audit", "ssl_check", "firewall", "updates", "suspicious", "integrity"]),
        "text": _p("Input text"), "password": _p("Password to check"),
        "length": _p("Password/token length", "integer"),
        "words": _p("Passphrase word count", "integer"),
        "algorithm": _p("Hash algorithm"), "path": _p("File path"),
        "hostname": _p("Hostname for SSL check"), "host": _p("Host for port audit"),
        "key": _p("HMAC key"), "shift": _p("Caesar shift", "integer"),
        "directory": _p("Directory for integrity check"),
        "save": _p("Save integrity baseline", "boolean"),
    }, ["operation"]),

    # ── Calendar ──────────────────────────────────────────
    _tool("calendar_operation", "Full calendar: add/list/search/cancel events, recurring events, free slots, iCal export", {
        "operation": _p("Operation", enum=["add", "get", "update", "cancel", "delete", "list", "today", "week", "search", "categories", "export", "free_slots", "summary"]),
        "title": _p("Event title"), "start": _p("Start date/time"),
        "end": _p("End date/time"), "description": _p("Event description"),
        "location": _p("Event location"), "category": _p("Event category"),
        "recurrence": _p("Recurrence: daily, weekly, monthly, yearly"),
        "event_id": _p("Event ID", "integer"), "query": _p("Search query"),
        "days": _p("Number of days to list", "integer"),
        "attendees": _p("Comma-separated attendee names"),
        "date": _p("Date for free slots"), "duration_hours": _p("Duration in hours", "integer"),
    }, ["operation"]),

    # ── Workflow Engine ───────────────────────────────────
    _tool("workflow_operation", "Automated workflows: create, run, manage multi-step pipelines with templates", {
        "operation": _p("Operation", enum=["create", "add_step", "remove_step", "delete", "get", "list", "run", "stop", "template"]),
        "name": _p("Workflow name"), "description": _p("Workflow description"),
        "step_name": _p("Step name"), "action": _p("Tool name for step"),
        "params": {"type": "object", "description": "Step parameters"},
        "condition": _p("Step condition expression"),
        "on_error": _p("Error handling: stop, skip, retry"),
        "template": _p("Template: morning_routine, system_health, backup_project, end_of_day"),
        "store_as": _p("Variable name to store result"),
        "step_index": _p("Step index to remove", "integer"),
    }, ["operation"]),

    # ── Health Tracker ────────────────────────────────────
    _tool("health_operation", "Health & fitness: water, exercise, sleep, weight, meals, mood, steps, BMI, goals", {
        "operation": _p("Operation", enum=["water", "water_today", "exercise", "exercise_today", "sleep", "sleep_avg", "weight", "weight_history", "meal", "calories_today", "mood", "steps", "set_goal", "goals", "profile", "bmi", "summary", "weekly"]),
        "glasses": _p("Water glasses", "integer"), "type": _p("Exercise type"),
        "duration": _p("Duration in minutes", "integer"), "calories": _p("Calories", "integer"),
        "hours": _p("Sleep hours", "number"), "quality": _p("Sleep quality: poor, fair, good, excellent"),
        "kg": _p("Weight in kg", "number"), "description": _p("Meal description"),
        "meal_type": _p("Meal type: breakfast, lunch, dinner, snack"),
        "mood": _p("Mood: amazing, happy, good, neutral, tired, stressed, sad"),
        "count": _p("Step count", "integer"), "goal_type": _p("Goal type"),
        "value": _p("Goal value", "number"), "notes": _p("Additional notes"),
        "height_cm": _p("Height in cm", "integer"), "age": _p("Age", "integer"),
        "gender": _p("Gender"),
    }, ["operation"]),

    # ── Project Scaffolder ────────────────────────────────
    _tool("scaffold_project", "Create new project boilerplate for various frameworks", {
        "project_type": _p("Type", enum=["python", "python_api", "flask", "django", "node", "node_api", "react", "html", "cli", "chrome_extension", "electron", "arduino"]),
        "project_name": _p("Project name"),
        "output_dir": _p("Output directory (default: ~/Projects)"),
    }, ["project_type", "project_name"]),
    _tool("list_project_templates", "List available project scaffolding templates"),

    # ── SSH Manager ───────────────────────────────────────
    _tool("ssh_operation", "SSH remote management: add hosts, execute commands, SCP uploads/downloads", {
        "operation": _p("Operation", enum=["add", "remove", "list", "exec", "upload", "download", "test", "info"]),
        "name": _p("Host name/alias"), "hostname": _p("SSH hostname/IP"),
        "username": _p("SSH username"), "port": _p("SSH port", "integer"),
        "command": _p("Remote command"), "key_file": _p("SSH key file path"),
        "local_path": _p("Local file path"), "remote_path": _p("Remote file path"),
        "description": _p("Host description"),
    }, ["operation"]),

    # ── System Optimizer ──────────────────────────────────
    _tool("optimizer_operation", "System optimization: disk cleanup, large files, duplicates, memory, startup, health score", {
        "operation": _p("Operation", enum=["cleanup", "disk_usage", "large_files", "duplicates", "memory_cleanup", "startup", "health_score", "env", "set_env"]),
        "path": _p("Directory path"), "aggressive": _p("Aggressive cleanup", "boolean"),
        "min_size_mb": _p("Minimum file size in MB", "integer"),
        "search": _p("Search term for env vars"),
        "key": _p("Environment variable name"), "value": _p("Environment variable value"),
        "permanent": _p("Set env var permanently", "boolean"),
    }, ["operation"]),

    # ── Notifications ─────────────────────────────────────
    _tool("notification_operation", "Send notifications via desktop, email, Slack, Discord, Telegram, webhooks", {
        "operation": _p("Operation", enum=["send", "desktop", "add_channel", "remove_channel", "list_channels", "history", "clear", "add_rule", "list_rules"]),
        "title": _p("Notification title"), "message": _p("Notification message"),
        "channel_type": _p("Channel type: desktop, email, slack, discord, telegram, webhook"),
        "channels": _p("Comma-separated channel names to send to"),
        "webhook_url": _p("Webhook URL"), "bot_token": _p("Telegram bot token"),
        "chat_id": _p("Telegram chat ID"), "name": _p("Channel name"),
    }, ["operation"]),

    # ── Data Visualization ────────────────────────────────
    _tool("visualization_operation", "Create SVG charts: bar, line, pie, horizontal bar, gauge, sparkline", {
        "operation": _p("Operation", enum=["bar", "line", "pie", "horizontal_bar", "gauge", "sparkline", "from_csv"]),
        "data": {"type": "object", "description": "Data as {label: value} object"},
        "title": _p("Chart title"), "value": _p("Gauge value", "number"),
        "max_value": _p("Gauge max value", "number"),
        "values": {"type": "array", "items": {"type": "number"}, "description": "Sparkline values"},
        "csv_path": _p("CSV file path"), "chart_type": _p("Chart type for CSV"),
    }, ["operation"]),

    # ── Home Inventory ────────────────────────────────────
    _tool("inventory_operation", "Home inventory: track possessions, electronics, warranties, serial numbers", {
        "operation": _p("Operation", enum=["add", "get", "update", "delete", "list", "search", "categories", "locations", "warranty", "value", "export"]),
        "name": _p("Item name"), "category": _p("Category: electronics, furniture, kitchen, etc."),
        "location": _p("Storage location"), "price": _p("Purchase price", "number"),
        "serial": _p("Serial number"), "model": _p("Model name/number"),
        "brand": _p("Brand name"), "warranty": _p("Warranty expiry date YYYY-MM-DD"),
        "condition": _p("Condition: excellent, good, fair, poor"),
        "quantity": _p("Quantity", "integer"), "item_id": _p("Item ID", "integer"),
        "query": _p("Search query"), "sort_by": _p("Sort: name, price, date, category"),
        "notes": _p("Additional notes"),
    }, ["operation"]),
]


class JarvisBrain:
    """Core AI reasoning engine with tool-calling capabilities."""

    def __init__(self):
        self.memory = ConversationMemory()
        self.persistent = PersistentMemory(config.MEMORY_DIR)
        self.tool_handlers: dict = {}
        self._thinking = False

        # Register memory tools internally
        self.register_tool("remember", self.persistent.store_fact)
        self.register_tool("recall", self.persistent.recall_fact)
        self.register_tool("list_memories", self.persistent.list_facts)
        self.register_tool("forget", self.persistent.forget_fact)
        self.register_tool("set_preference", self.persistent.set_preference)
        self.register_tool("search_history", self.persistent.search_history)

    def register_tool(self, name: str, handler):
        """Register a callable tool handler."""
        self.tool_handlers[name] = handler

    async def think(self, user_input: str, broadcast=None) -> str:
        """
        Process user input. Uses OpenAI if available, otherwise falls back
        to local pattern-matching command engine.
        """
        global _openai_available, _openai_failed_permanently
        self._thinking = True
        self.memory.add("user", user_input)

        # ─── Try OpenAI first (skip if it failed permanently) ─
        if _openai_available and client and not _openai_failed_permanently:
            result = await self._think_openai(user_input, broadcast)
            if not result.startswith("I'm having trouble connecting"):
                self.memory.add("assistant", result)
                self.persistent.log_exchange(user_input, result)
                self._thinking = False
                return result
            # If 401/invalid key, stop trying OpenAI for this session
            if "401" in result or "invalid_api_key" in result or "Incorrect API key" in result:
                _openai_failed_permanently = True

        # ─── Try local Ollama LLM as second fallback ──────────
        try:
            from modules.ollama_llm import ask_ollama, is_ollama_available
            if await is_ollama_available():
                ollama_reply = await ask_ollama(
                    user_input,
                    system_prompt=("You are J.A.R.V.I.S., a helpful AI assistant. "
                                   "Be concise, witty, and helpful. Current time: "
                                   + datetime.now().strftime('%Y-%m-%d %H:%M')),
                )
                if ollama_reply and not ollama_reply.startswith("Ollama error"):
                    self.memory.add("assistant", ollama_reply)
                    self.persistent.log_exchange(user_input, ollama_reply)
                    self._thinking = False
                    return ollama_reply
        except Exception:
            pass

        # ─── Offline fallback — local command matching ────────
        result = await self._think_offline(user_input, broadcast)
        self.memory.add("assistant", result)
        self.persistent.log_exchange(user_input, result)
        self._thinking = False
        return result

    async def _think_openai(self, user_input: str, broadcast=None) -> str:
        """Process via OpenAI API with tool calling."""
        context_extra = self.persistent.get_context_summary()
        system_content = config.SYSTEM_PROMPT + f"\n\nCurrent time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        if context_extra:
            system_content += f"\n\nStored knowledge:\n{context_extra}"

        messages = [
            {"role": "system", "content": system_content},
            *self.memory.get_messages(),
        ]

        try:
            response = await client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=4096,
            )
        except Exception as e:
            return f"I'm having trouble connecting to my reasoning engine: {e}"

        msg = response.choices[0].message

        max_iterations = 10
        iteration = 0
        while msg.tool_calls and iteration < max_iterations:
            iteration += 1
            messages.append(msg)

            for tc in msg.tool_calls:
                fn_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                if broadcast:
                    await broadcast(json.dumps({
                        "type": "tool_call",
                        "tool": fn_name,
                        "args": args,
                    }))

                result = await self._execute_tool(fn_name, args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result)[:6000],
                })

            try:
                response = await client.chat.completions.create(
                    model=config.OPENAI_MODEL,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    temperature=0.7,
                    max_tokens=4096,
                )
            except Exception as e:
                return f"Error during tool follow-up: {e}"

            msg = response.choices[0].message

        return msg.content or "Done."

    async def _think_offline(self, user_input: str, broadcast=None) -> str:
        """
        Offline command engine — matches user input to tools via patterns.
        Works without any API key.
        """
        text = user_input.lower().strip()

        # ─── Direct command patterns ──────────────────────────
        PATTERNS = [
            # System
            (r'\b(system info|system status|system report|my system)\b', 'system_info', {}),
            (r'\b(open|launch|start)\s+(.+)', 'open_application', lambda m: {"app_name": m.group(2).strip()}),
            (r'\b(close|kill|quit|exit)\s+(.+)', 'close_application', lambda m: {"app_name": m.group(2).strip()}),
            (r'\b(running processes|list processes|top processes)\b', 'list_running_processes', {}),
            (r'\bscreenshot\b', 'screenshot', {}),
            (r'\b(lock|lock screen|lock computer)\b', 'system_power', {"action": "lock"}),
            (r'\b(shutdown|shut down)\b', 'system_power', {"action": "shutdown"}),
            (r'\brestart\b', 'system_power', {"action": "restart"}),
            (r'\bsleep\b', 'system_power', {"action": "sleep"}),
            (r'\bvolume\s+(\d+)', 'set_volume', lambda m: {"level": int(m.group(1))}),
            (r'\bbrightness\s+(\d+)', 'set_brightness', lambda m: {"level": int(m.group(1))}),
            (r'\bmute\b', 'set_volume', {"level": 0}),

            # Time & Weather
            (r'\b(what time|current time|time now|date today|what date)\b', 'get_datetime_info', {}),
            (r'\bweather\s*(in|for|at)?\s*(.+)?', 'get_weather', lambda m: {"location": (m.group(2) or "").strip() or "auto"}),

            # Files
            (r'\b(list|show|ls)\s+(files|directory|folder|dir)\s*(in|of|at)?\s*(.+)?', 'list_directory', lambda m: {"dir_path": (m.group(4) or ".").strip()}),
            (r'\bread\s+(file\s+)?(.+\.\w+)', 'read_file', lambda m: {"file_path": m.group(2).strip()}),
            (r'\bcreate\s+file\s+(.+)', 'create_file', lambda m: {"file_path": m.group(1).strip(), "content": ""}),

            # Media
            (r'\bplay\s+(.+)\s+on\s+youtube\b', 'play_youtube', lambda m: {"query": m.group(1).strip()}),
            (r'\bplay\s+(youtube|video)\s+(.+)', 'play_youtube', lambda m: {"query": m.group(2).strip()}),
            (r'\b(play|pause|next|previous|stop)\s*(music|song|track|media)?\b', 'control_media', lambda m: {"action": m.group(1).strip()}),
            (r'\bsearch\s+youtube\s+(.+)', 'youtube_search', lambda m: {"query": m.group(1).strip()}),
            (r'\bsearch\s+spotify\s+(.+)', 'spotify_search', lambda m: {"query": m.group(1).strip()}),
            (r'\bopen\s+(https?://\S+)', 'open_url', lambda m: {"url": m.group(1)}),

            # Web
            (r'\b(search|google|look up|find)\s+(for\s+)?(.+)', 'web_search', lambda m: {"query": m.group(3).strip()}),
            (r'\bnews\s*(about|on)?\s*(.+)?', 'get_news', lambda m: {"topic": (m.group(2) or "technology").strip()}),

            # Translate
            (r'\btranslate\s+["\']?(.+?)["\']?\s+to\s+(\w+)', 'translate_text', lambda m: {"text": m.group(1), "to_lang": m.group(2)}),

            # Calculate
            (r'\b(calculate|calc|math|compute)\s+(.+)', 'calculate', lambda m: {"expression": m.group(2).strip()}),
            (r'^[\d\s\+\-\*/\(\)\.\^%]+$', 'calculate', lambda m: {"expression": m.group(0).strip()}),

            # Clipboard
            (r'\b(copy|clipboard)\s+(.+)', 'clipboard_write', lambda m: {"text": m.group(2).strip()}),
            (r'\bpaste\b|clipboard\s+read', 'clipboard_read', {}),

            # Tasks
            (r'\b(add task|new task|create task)\s+(.+)', 'task_operation', lambda m: {"operation": "add", "title": m.group(2).strip()}),
            (r'\b(my tasks|list tasks|show tasks|task list)\b', 'task_operation', {"operation": "list"}),
            (r'\btask summary\b', 'task_operation', {"operation": "summary"}),
            (r'\btoday.?s tasks\b', 'task_operation', {"operation": "today"}),

            # Notes
            (r'\b(add note|new note|create note)\s+(.+)', 'note_operation', lambda m: {"operation": "create", "title": m.group(2).strip()[:50], "content": m.group(2).strip()}),
            (r'\b(my notes|list notes|show notes)\b', 'note_operation', {"operation": "list"}),

            # Reminders
            (r'\bremind\s+me\s+(in\s+)?(\d+)\s*(min|minute|minutes|sec|second|seconds|hour|hours)\s+(.+)', 'set_reminder', lambda m: {
                "message": m.group(4).strip(),
                "seconds": int(m.group(2)) * ({"min": 60, "minute": 60, "minutes": 60, "sec": 1, "second": 1, "seconds": 1, "hour": 3600, "hours": 3600}.get(m.group(3), 60))
            }),

            # ESP32 / IoT
            (r'\b(temperature|humidity|sensor|esp32)\b.*\bread\b|\bread\b.*\b(temperature|humidity|sensor|esp32)\b', 'esp32_read_sensors', {}),
            (r'\b(turn on|enable)\s+(the\s+)?(led|light)\b', 'esp32_control', {"command": "LED_ON"}),
            (r'\b(turn off|disable)\s+(the\s+)?(led|light)\b', 'esp32_control', {"command": "LED_OFF"}),

            # Git
            (r'\bgit\s+status\b', 'git_operation', {"operation": "status"}),
            (r'\bgit\s+log\b', 'git_operation', {"operation": "log"}),
            (r'\bgit\s+diff\b', 'git_operation', {"operation": "diff"}),
            (r'\bgit\s+pull\b', 'git_operation', {"operation": "pull"}),
            (r'\bgit\s+push\b', 'git_operation', {"operation": "push"}),

            # Network
            (r'\bping\s+(\S+)', 'ping_host', lambda m: {"host": m.group(1)}),
            (r'\b(network info|network status|network scan)\b', 'network_scan', {}),
            (r'\bip\s+info\b', 'network_tool', {"operation": "ip_info"}),

            # Docker
            (r'\bdocker\s+ps\b', 'docker_operation', {"operation": "ps"}),
            (r'\bdocker\s+images\b', 'docker_operation', {"operation": "images"}),

            # Fun / Personality
            (r'\b(tell me a joke|joke)\b', 'tell_joke', {}),
            (r'\b(fun fact|random fact)\b', 'fun_fact', {}),
            (r'\b(motivat|inspir|quote)\b', 'motivational_quote', {}),
            (r'\b(daily briefing|morning briefing|briefing)\b', 'get_daily_briefing', {}),

            # Health
            (r'\blog\s+(\d+)\s+glass', 'health_operation', lambda m: {"operation": "water", "glasses": int(m.group(1))}),
            (r'\bdrank\s+water\b|log\s+water\b', 'health_operation', {"operation": "water", "glasses": 1}),

            # Calendar
            (r'\b(today.?s events|calendar today|what.?s on today)\b', 'calendar_operation', {"operation": "today"}),
            (r'\bthis week.?s events\b', 'calendar_operation', {"operation": "week"}),

            # Pomodoro
            (r'\bstart\s+pomodoro\b|focus\s+timer\b', 'pomodoro_operation', {"operation": "start"}),
            (r'\bstop\s+pomodoro\b', 'pomodoro_operation', {"operation": "stop"}),

            # Expenses
            (r'\bspent\s+\$?(\d+\.?\d*)\s+on\s+(.+)', 'expense_operation', lambda m: {"operation": "add", "amount": float(m.group(1)), "description": m.group(2).strip()}),

            # Activity tracking
            (r'\bwhat did I do today\b|today.?s activity\b', 'activity_operation', {"operation": "today"}),
            (r'\bapp\s+usage\b|my app\s+stats\b', 'activity_operation', {"operation": "apps"}),
            (r'\bstart\s+tracking\b|track\s+activity\b', 'activity_operation', {"operation": "start"}),

            # Gmail
            (r'\b(check|read)\s+(my\s+)?gmail\b', 'gmail_operation', {"operation": "check"}),
            (r'\bsummarize\s+(my\s+)?gmail\b|gmail\s+summary\b', 'gmail_operation', {"operation": "summarize"}),
            (r'\bgmail\s+setup\b', 'gmail_operation', {"operation": "setup"}),

            # Ollama/local LLM
            (r'\b(ollama|local)\s+models?\b|list\s+ollama\b', '_ollama_models', {}),

            # System optimizer
            (r'\bhealth\s+score\b|system\s+health\b', 'optimizer_operation', {"operation": "health_score"}),
            (r'\bclean\s*(up)?\s*(disk|temp|junk)\b', 'optimizer_operation', {"operation": "cleanup"}),

            # Help
            (r'\b(help|what can you do|commands|capabilities)\b', '_help', {}),

            # WhatsApp
            (r'\bsend\s+whatsapp\s+to\s+(\S+)\s+(.+)', 'send_whatsapp', lambda m: {"to": m.group(1), "message": m.group(2).strip()}),

            # Email
            (r'\b(check|read)\s+(my\s+)?emails?\b', 'read_emails', {}),
            (r'\bunread\s+emails?\b', 'count_unread_emails', {}),

            # WiFi
            (r'\bwifi\s+(list|scan|networks)\b', 'wifi_control', {"action": "list"}),
            (r'\bwifi\s+status\b', 'wifi_control', {"action": "status"}),

            # QR Code
            (r'\b(generate|create|make)\s+qr\s*(code)?\s+(.+)', 'generate_qr_code', lambda m: {"data": m.group(3).strip()}),

            # Vision
            (r'\b(what do you see|look at|see)\s*(the\s+)?(screen|monitor|display)\b', 'live_vision', {"operation": "screen"}),
            (r'\b(what.?s on|read)\s*(my\s+)?(screen|monitor)\b', 'live_vision', {"operation": "read_screen"}),
            (r'\b(look at|see|show)\s*(the\s+)?camera\b', 'live_vision', {"operation": "camera"}),
            (r'\b(what app|which app|what.?s open|active window)\b', 'live_vision', {"operation": "what_app"}),
            (r'\b(describe|show me)\s+what you see\b', 'live_vision', {"operation": "see"}),
            (r'\bdetect objects\b', 'live_vision', {"operation": "detect_objects"}),
            (r'\bcapture\s+(screen|camera)\b', 'live_vision', lambda m: {"operation": "capture", "source": m.group(1)}),
            (r'\blist\s+cameras\b', 'live_vision', {"operation": "list_cameras"}),

            # Language switch
            (r'\b(switch to|speak in|change language to|use)\s+(telugu|తెలుగు)\b', '_lang_te', {}),
            (r'\b(switch to|speak in|change language to|use)\s+english\b', '_lang_en', {}),
            (r'\btelugu\s+(lo|లో)\s+(matladu|మాట్లాడు)\b', '_lang_te', {}),
            (r'\bతెలుగులో మాట్లాడు\b', '_lang_te', {}),

            # ── Telugu Commands (తెలుగు) ─────────────────────
            (r'సమయం\s*ఎంత|ఇప్పుడు\s*సమయం', 'get_datetime_info', {}),
            (r'వాతావరణం|weather\s*చెప్పు', 'get_weather', {"location": "auto"}),
            (r'సిస్టమ్\s*సమాచారం|system\s*info\s*చెప్పు', 'system_info', {}),
            (r'జోక్\s*చెప్పు|joke\s*చెప్పు|ఒక\s*జోక్', 'tell_joke', {}),
            (r'స్క్రీన్\s*షాట్|screenshot\s*తీయి', 'screenshot', {}),
            (r'ఓపెన్\s+(.+)', 'open_application', lambda m: {"app_name": m.group(1).strip()}),
            (r'క్లోజ్\s+(.+)', 'close_application', lambda m: {"app_name": m.group(1).strip()}),
            (r'లాక్\s*చేయి|కంప్యూటర్\s*లాక్', 'system_power', {"action": "lock"}),
            (r'వాల్యూమ్\s*(\d+)', 'set_volume', lambda m: {"level": int(m.group(1))}),
            (r'న్యూస్|వార్తలు', 'get_news', {"topic": "technology"}),
            (r'సహాయం|help\s*చెప్పు|ఏం\s*చేయగలవు', '_help', {}),
            (r'రిమైండ్\s*చేయి\s+(\d+)\s*(నిమిషాల|నిమిషం).*?(.+)', 'set_reminder', lambda m: {"message": m.group(3).strip(), "seconds": int(m.group(1)) * 60}),
            (r'టాస్క్\s*జోడించు\s+(.+)', 'task_operation', lambda m: {"operation": "add", "title": m.group(1).strip()}),
            (r'నా\s*టాస్క్\s*లు|tasks\s*చూపించు', 'task_operation', {"operation": "list"}),
            (r'కాలిక్యులేట్\s+(.+)', 'calculate', lambda m: {"expression": m.group(1).strip()}),
            (r'ట్రాన్స్లేట్\s+(.+?)\s+(to|కి)\s+(\w+)', 'translate_text', lambda m: {"text": m.group(1), "to_lang": m.group(3)}),
            (r'శుభోదయం', 'get_daily_briefing', {}),
            (r'ధన్యవాదాలు|thanks\s*చెప్పు', '_thanks', {}),
            (r'ప్రక్రియలు\s*చూపించు|running\s*processes\s*చూపించు', 'list_running_processes', {}),
            (r'కంప్యూటర్\s*ఆపు|shutdown\s*చేయి', 'system_power', {"action": "shutdown"}),
            (r'రీస్టార్ట్\s*చేయి', 'system_power', {"action": "restart"}),
            (r'ఫైల్స్\s*చూపించు|ఫైళ్లు\s*చూపించు', 'list_directory', {"dir_path": "."}),
            (r'నెట్వర్క్\s*సమాచారం', 'network_scan', {}),
        ]

        # Try each pattern
        for pattern, tool_name, args_or_fn in PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Handle special commands
                if tool_name == '_help':
                    return self._get_help_text()
                if tool_name == '_lang_te':
                    return self._switch_language("te")
                if tool_name == '_lang_en':
                    return self._switch_language("en")
                if tool_name == '_thanks':
                    return "మీకు స్వాగతం! (You're welcome!) I'm always here to help."
                if tool_name == '_ollama_models':
                    try:
                        from modules.ollama_llm import list_ollama_models
                        return asyncio.get_event_loop().run_until_complete(list_ollama_models())
                    except Exception:
                        return "Ollama not available."

                # Build args
                if callable(args_or_fn):
                    args = args_or_fn(match)
                else:
                    args = dict(args_or_fn)

                # Broadcast tool call
                if broadcast:
                    await broadcast(json.dumps({
                        "type": "tool_call",
                        "tool": tool_name,
                        "args": args,
                    }))

                # Execute tool
                result = await self._execute_tool(tool_name, args)
                return f"{result}"

        # ─── No pattern matched — try to be helpful ──────────
        # Check if it looks like a command and suggest
        if any(word in text for word in ["open", "close", "run", "start", "show", "list", "get", "set", "create", "delete"]):
            return (
                f"I understood you want to do something, but I'm running in offline mode "
                f"(no AI engine). Try being more specific, like:\n"
                f"  - 'open chrome'\n"
                f"  - 'system info'\n"
                f"  - 'what time is it'\n"
                f"  - 'weather in London'\n"
                f"  - 'play music on youtube'\n"
                f"  - Type 'help' for all commands"
            )

        return (
            f"I'm running in offline mode (AI engine unavailable). "
            f"I can still execute direct commands like:\n"
            f"  - System: 'system info', 'screenshot', 'open notepad'\n"
            f"  - Media: 'play [song] on youtube', 'next track'\n"
            f"  - Files: 'list files in .', 'read file config.py'\n"
            f"  - Tools: 'weather', 'calculate 2+2', 'ping google.com'\n"
            f"  - Tasks: 'add task [name]', 'my tasks'\n"
            f"  - Fun: 'tell me a joke', 'daily briefing'\n"
            f"\nType 'help' for the full list. Set a valid OPENAI_API_KEY for full AI mode."
        )

    def _get_help_text(self) -> str:
        """Return help text listing available offline commands."""
        return (
            "J.A.R.V.I.S. Commands (Offline Mode):\n\n"
            "SYSTEM:\n"
            "  system info | screenshot | lock | shutdown | restart | sleep\n"
            "  open [app] | close [app] | running processes\n"
            "  volume [0-100] | brightness [0-100] | mute\n"
            "  health score | clean disk | wifi list | wifi status\n\n"
            "MEDIA:\n"
            "  play [query] on youtube | search spotify [query]\n"
            "  play | pause | next | previous | stop\n"
            "  open [url]\n\n"
            "INFORMATION:\n"
            "  what time is it | weather in [city]\n"
            "  search [query] | news about [topic]\n"
            "  translate [text] to [language]\n"
            "  calculate [expression] | ping [host]\n\n"
            "FILES:\n"
            "  list files in [path] | read file [path]\n"
            "  create file [path]\n\n"
            "PRODUCTIVITY:\n"
            "  add task [title] | my tasks | task summary\n"
            "  add note [text] | my notes\n"
            "  remind me in [N] minutes [message]\n"
            "  today's events | start pomodoro\n"
            "  spent $[amount] on [description]\n\n"
            "IOT:\n"
            "  read temperature | turn on led | turn off led\n\n"
            "GIT:\n"
            "  git status | git log | git diff | git pull | git push\n\n"
            "FUN:\n"
            "  tell me a joke | fun fact | motivational quote\n"
            "  daily briefing\n\n"
            "OTHER:\n"
            "  check emails | unread emails | send whatsapp to [number] [msg]\n"
            "  generate qr code [data] | docker ps | network info\n\n"
            f"Total registered tools: {len(self.tool_handlers)}\n"
            "Set OPENAI_API_KEY for full AI-powered conversation mode."
        )

    def _switch_language(self, lang: str) -> str:
        """Switch TTS/STT language at runtime."""
        try:
            # Import voice engine from server context
            from api.server import voice
            result = voice.set_language(lang)
            if lang == "te":
                return (
                    f"{result}\n\n"
                    "తెలుగులో మాట్లాడటానికి సిద్ధంగా ఉన్నాను!\n"
                    "(Ready to speak in Telugu!)\n\n"
                    "తెలుగు కమాండ్ లు:\n"
                    "  సమయం ఎంత — What time is it\n"
                    "  వాతావరణం — Weather\n"
                    "  సిస్టమ్ సమాచారం — System info\n"
                    "  జోక్ చెప్పు — Tell a joke\n"
                    "  ఓపెన్ [app] — Open app\n"
                    "  లాక్ చేయి — Lock computer\n"
                    "  వార్తలు — News\n"
                    "  సహాయం — Help\n"
                )
            else:
                return f"{result}\n\nSwitched back to English. All commands available."
        except Exception as e:
            return f"Language switch error: {e}"

    async def _execute_tool(self, name: str, args: dict) -> str:
        handler = self.tool_handlers.get(name)
        if not handler:
            return f"Tool '{name}' is not registered."
        try:
            result = handler(**args)
            if asyncio.iscoroutine(result):
                result = await result
            return str(result)
        except Exception as e:
            return f"Tool error ({name}): {e}"
