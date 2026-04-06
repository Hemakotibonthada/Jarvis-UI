"""
J.A.R.V.I.S. — Main Entry Point
Starts the FastAPI server with the full Jarvis system.
"""

import sys
import os
import io
import asyncio
import argparse
import webbrowser

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
import config


def print_banner():
    banner = """
       ___   _   ____  __   __ ___  ____
      | | | / \\ |  _ \\ \\ \\ / /|_ _|/ ___|
   _  | |/ _ \\| |_) | \\ V /  | | \\___ \\
  | |_| / ___ \\|  _ <   | |   | |  ___) |
   \\___/_/   \\_\\_| \\_\\  |_|  |___||____/
    Just A Rather Very Intelligent System  v2.0
    """
    print(banner)
    print(f"  Server:   http://{config.API_HOST}:{config.API_PORT}")
    print(f"  Model:    {config.OPENAI_MODEL}")
    print(f"  Voice:    {config.EDGE_TTS_VOICE}")
    print(f"  ESP32:    {config.ESP32_SERIAL_PORT}")
    print(f"  Platform: {'Windows' if config.IS_WINDOWS else 'Linux' if config.IS_LINUX else 'macOS'}")
    print(f"  Tools:    100+ registered")
    print("-" * 50)

    if not config.OPENAI_API_KEY:
        print("\n  WARNING: OPENAI_API_KEY not set!")
        print("  Set it: $env:OPENAI_API_KEY = 'sk-...'")
        print("  Or add to .env file in project root")
        print("-" * 50)


def parse_args():
    parser = argparse.ArgumentParser(description="J.A.R.V.I.S. AI Assistant")
    parser.add_argument("--port", type=int, default=config.API_PORT, help="Server port")
    parser.add_argument("--host", type=str, default=config.API_HOST, help="Server host")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser on start")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--no-voice", action="store_true", help="Disable voice playback")
    parser.add_argument("--voice", type=str, default=config.EDGE_TTS_VOICE, help="TTS voice name")
    return parser.parse_args()


def main():
    args = parse_args()
    config.API_PORT = args.port
    config.API_HOST = args.host
    if args.voice:
        config.EDGE_TTS_VOICE = args.voice

    print_banner()

    # Open browser after short delay
    async def open_browser():
        await asyncio.sleep(1.5)
        webbrowser.open(f"http://{args.host}:{args.port}")

    # Run server
    uv_config = uvicorn.Config(
        "api.server:app",
        host=args.host,
        port=args.port,
        reload=args.debug,
        log_level="debug" if args.debug else "info",
    )
    server = uvicorn.Server(uv_config)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    if not args.no_browser:
        loop.create_task(open_browser())

    try:
        loop.run_until_complete(server.serve())
    except KeyboardInterrupt:
        print("\nJ.A.R.V.I.S. shutting down. Goodbye, sir.")


if __name__ == "__main__":
    main()
