"""
Media & Entertainment Module — YouTube, Spotify, music playback control.
"""

import subprocess
import webbrowser
import urllib.parse
import aiohttp
from pathlib import Path


async def youtube_search(query: str) -> str:
    """Search YouTube and return top results."""
    try:
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        webbrowser.open(url)
        return f"Opened YouTube search for: {query}"
    except Exception as e:
        return f"YouTube search error: {e}"


async def play_youtube(query: str) -> str:
    """Play the first YouTube result for a query."""
    try:
        import pywhatkit
        pywhatkit.playonyt(query)
        return f"Playing '{query}' on YouTube."
    except ImportError:
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        webbrowser.open(url)
        return f"Opened YouTube search for: {query}. Select a video to play."
    except Exception as e:
        return f"YouTube play error: {e}"


def control_media(action: str) -> str:
    """Control media playback: play, pause, next, previous, volume_up, volume_down."""
    try:
        import pyautogui
        actions = {
            "play": "playpause",
            "pause": "playpause",
            "play_pause": "playpause",
            "next": "nexttrack",
            "previous": "prevtrack",
            "prev": "prevtrack",
            "volume_up": "volumeup",
            "volume_down": "volumedown",
            "mute": "volumemute",
            "stop": "stop",
        }
        key = actions.get(action.lower())
        if key:
            pyautogui.press(key)
            return f"Media action: {action}"
        return f"Unknown media action: {action}. Available: {', '.join(actions.keys())}"
    except ImportError:
        return "pyautogui not installed."


async def spotify_search(query: str) -> str:
    """Search Spotify via web."""
    try:
        url = f"https://open.spotify.com/search/{urllib.parse.quote(query)}"
        webbrowser.open(url)
        return f"Opened Spotify search for: {query}"
    except Exception as e:
        return f"Spotify search error: {e}"


def open_url(url: str) -> str:
    """Open a URL in the default browser."""
    try:
        webbrowser.open(url)
        return f"Opened: {url}"
    except Exception as e:
        return f"Failed to open URL: {e}"


def get_system_audio_devices() -> str:
    """List system audio input/output devices."""
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        devices = []
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            dev_type = []
            if info["maxInputChannels"] > 0:
                dev_type.append("INPUT")
            if info["maxOutputChannels"] > 0:
                dev_type.append("OUTPUT")
            devices.append(
                f"  [{i}] {info['name']} ({', '.join(dev_type)}) "
                f"— {info['defaultSampleRate']:.0f}Hz"
            )
        p.terminate()
        return f"Audio Devices ({len(devices)}):\n" + "\n".join(devices)
    except ImportError:
        return "PyAudio not installed."
    except Exception as e:
        return f"Audio device error: {e}"


def get_playing_media() -> str:
    """Get currently playing media info (Windows)."""
    import config
    if not config.IS_WINDOWS:
        return "Media detection only supported on Windows."
    try:
        result = subprocess.run(
            ['powershell', '-c',
             'Get-Process | Where-Object {$_.MainWindowTitle -ne ""} | '
             'Where-Object {$_.ProcessName -match "spotify|chrome|firefox|edge|vlc|wmplayer|groove|musicbee"} | '
             'Select-Object ProcessName,MainWindowTitle | Format-List'],
            capture_output=True, text=True, timeout=5,
        )
        output = result.stdout.strip()
        return f"Media Players Active:\n{output}" if output else "No media players detected."
    except Exception as e:
        return f"Media detection error: {e}"


def set_default_audio_device(device_name: str) -> str:
    """Set the default audio output device (Windows)."""
    import config
    if not config.IS_WINDOWS:
        return "Only supported on Windows."
    try:
        result = subprocess.run(
            ['powershell', '-c',
             f'$dev = Get-AudioDevice -List | Where-Object {{$_.Name -like "*{device_name}*"}} | Select-Object -First 1; '
             f'if ($dev) {{ Set-AudioDevice -ID $dev.ID; "Set to: $($dev.Name)" }} else {{ "Device not found" }}'],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip() or "Could not set audio device."
    except Exception as e:
        return f"Audio device error: {e}"


async def get_lyrics(song: str, artist: str = "") -> str:
    """Get song lyrics from lyrics.ovh API."""
    try:
        search = f"{artist}/{song}" if artist else f"_/{song}"
        url = f"https://api.lyrics.ovh/v1/{urllib.parse.quote(search)}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    lyrics = data.get("lyrics", "")
                    if lyrics:
                        return f"🎵 {song}" + (f" — {artist}" if artist else "") + f"\n\n{lyrics[:3000]}"
                    return "Lyrics not found."
                return f"Lyrics API returned status {resp.status}"
    except Exception as e:
        return f"Lyrics error: {e}"


def create_playlist_file(name: str, songs: list[str], output_dir: str = "") -> str:
    """Create an M3U playlist file."""
    from pathlib import Path
    import config
    
    if not output_dir:
        output_dir = str(config.GENERATED_DIR)
    
    safe_name = "".join(c if c.isalnum() or c in " -_" else "" for c in name)[:50]
    path = Path(output_dir) / f"{safe_name}.m3u"
    
    content = "#EXTM3U\n"
    for song in songs:
        content += f"#EXTINF:-1,{Path(song).stem}\n{song}\n"
    
    path.write_text(content, encoding="utf-8")
    return f"Playlist created: {path} ({len(songs)} songs)"
