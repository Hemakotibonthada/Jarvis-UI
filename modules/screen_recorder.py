"""
Screen & Audio Recorder Module — Record screen, audio, and manage recordings.
"""

import subprocess
import threading
import time
import os
from datetime import datetime
from pathlib import Path
from core.logger import get_logger
import config

log = get_logger("recorder")


class ScreenRecorder:
    """Screen recording using FFmpeg."""

    def __init__(self):
        self._recording = False
        self._process = None
        self._output_file = ""
        self._start_time = None

    @property
    def is_recording(self) -> bool:
        return self._recording

    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available."""
        try:
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def start_recording(self, output_name: str = "", fps: int = 30,
                        audio: bool = True) -> str:
        """Start screen recording."""
        if self._recording:
            return "Already recording. Stop the current recording first."

        if not self._check_ffmpeg():
            return "FFmpeg not found. Install it: https://ffmpeg.org/download.html"

        if not output_name:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_name = f"recording_{ts}.mp4"

        self._output_file = str(config.GENERATED_DIR / output_name)

        # Build FFmpeg command based on platform
        if config.IS_WINDOWS:
            cmd = [
                "ffmpeg", "-y",
                "-f", "gdigrab",
                "-framerate", str(fps),
                "-i", "desktop",
            ]
            if audio:
                cmd.extend([
                    "-f", "dshow",
                    "-i", "audio=virtual-audio-capturer",
                ])
            cmd.extend([
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                self._output_file,
            ])
        elif config.IS_LINUX:
            cmd = [
                "ffmpeg", "-y",
                "-f", "x11grab",
                "-framerate", str(fps),
                "-i", ":0.0",
            ]
            if audio:
                cmd.extend(["-f", "pulse", "-i", "default"])
            cmd.extend([
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "23",
                self._output_file,
            ])
        else:  # macOS
            cmd = [
                "ffmpeg", "-y",
                "-f", "avfoundation",
                "-framerate", str(fps),
                "-i", "1:0" if audio else "1:",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                self._output_file,
            ]

        try:
            self._process = subprocess.Popen(
                cmd, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self._recording = True
            self._start_time = time.time()
            log.info(f"Screen recording started: {self._output_file}")
            return f"Screen recording started. Output: {self._output_file}"
        except Exception as e:
            return f"Failed to start recording: {e}"

    def stop_recording(self) -> str:
        """Stop the current recording."""
        if not self._recording or not self._process:
            return "No active recording."

        try:
            # Send 'q' to FFmpeg to stop gracefully
            self._process.stdin.write(b"q")
            self._process.stdin.flush()
            self._process.wait(timeout=10)
        except Exception:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                self._process.kill()

        self._recording = False
        duration = time.time() - self._start_time if self._start_time else 0
        self._start_time = None

        file_size = Path(self._output_file).stat().st_size if Path(self._output_file).exists() else 0
        log.info(f"Screen recording stopped: {self._output_file} ({duration:.1f}s)")

        return (
            f"Recording stopped.\n"
            f"File: {self._output_file}\n"
            f"Duration: {duration:.1f} seconds\n"
            f"Size: {file_size / (1024 * 1024):.1f} MB"
        )

    def get_status(self) -> str:
        """Get recording status."""
        if not self._recording:
            return "Not recording."
        duration = time.time() - self._start_time if self._start_time else 0
        return f"Recording in progress: {duration:.1f}s — {self._output_file}"


class AudioRecorder:
    """Audio recording using built-in microphone."""

    def __init__(self):
        self._recording = False
        self._frames = []
        self._thread = None
        self._output_file = ""
        self._start_time = None

    def start_recording(self, output_name: str = "", duration: int = 0) -> str:
        """Start audio recording. If duration > 0, auto-stop after that many seconds."""
        if self._recording:
            return "Already recording audio."

        try:
            import pyaudio
            import wave
        except ImportError:
            return "PyAudio not installed. Run: pip install PyAudio"

        if not output_name:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_name = f"audio_{ts}.wav"

        self._output_file = str(config.GENERATED_DIR / output_name)
        self._frames = []
        self._recording = True
        self._start_time = time.time()

        def record_thread():
            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=44100,
                input=True,
                frames_per_buffer=1024,
            )

            while self._recording:
                if duration > 0 and (time.time() - self._start_time) >= duration:
                    break
                data = stream.read(1024, exception_on_overflow=False)
                self._frames.append(data)

            stream.stop_stream()
            stream.close()
            p.terminate()

            # Save to WAV file
            import wave
            wf = wave.open(self._output_file, "wb")
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(44100)
            wf.writeframes(b"".join(self._frames))
            wf.close()

            self._recording = False
            log.info(f"Audio recording saved: {self._output_file}")

        self._thread = threading.Thread(target=record_thread, daemon=True)
        self._thread.start()

        msg = f"Audio recording started: {self._output_file}"
        if duration:
            msg += f" (auto-stop in {duration}s)"
        return msg

    def stop_recording(self) -> str:
        """Stop audio recording."""
        if not self._recording:
            return "No active audio recording."

        self._recording = False
        if self._thread:
            self._thread.join(timeout=5)

        duration = time.time() - self._start_time if self._start_time else 0
        self._start_time = None
        file_size = Path(self._output_file).stat().st_size if Path(self._output_file).exists() else 0

        return (
            f"Audio recording stopped.\n"
            f"File: {self._output_file}\n"
            f"Duration: {duration:.1f} seconds\n"
            f"Size: {file_size / 1024:.1f} KB"
        )


async def transcribe_audio(file_path: str) -> str:
    """Transcribe an audio file using OpenAI Whisper API."""
    p = Path(file_path).expanduser()
    if not p.exists():
        return f"Audio file not found: {p}"

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        with open(p, "rb") as f:
            transcript = await client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
            )
        return f"Transcription of {p.name}:\n{transcript.text}"
    except ImportError:
        return "OpenAI library not installed."
    except Exception as e:
        return f"Transcription error: {e}"


def list_recordings() -> str:
    """List all recordings in the generated directory."""
    recordings = []
    for ext in ["*.mp4", "*.avi", "*.mkv", "*.wav", "*.mp3", "*.ogg"]:
        recordings.extend(config.GENERATED_DIR.glob(ext))

    if not recordings:
        return "No recordings found."

    recordings.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    lines = []
    for r in recordings[:30]:
        size = r.stat().st_size / (1024 * 1024)
        mtime = datetime.fromtimestamp(r.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        lines.append(f"  {r.name} ({size:.1f} MB) — {mtime}")

    return f"Recordings ({len(recordings)}):\n" + "\n".join(lines)


# ─── High-level control function ─────────────────────────────
screen_recorder = ScreenRecorder()
audio_recorder = AudioRecorder()


def recording_control(action: str, **kwargs) -> str:
    """Unified recording control."""
    if action == "start_screen":
        return screen_recorder.start_recording(
            kwargs.get("name", ""), kwargs.get("fps", 30), kwargs.get("audio", True)
        )
    elif action == "stop_screen":
        return screen_recorder.stop_recording()
    elif action == "start_audio":
        return audio_recorder.start_recording(
            kwargs.get("name", ""), kwargs.get("duration", 0)
        )
    elif action == "stop_audio":
        return audio_recorder.stop_recording()
    elif action == "status":
        screen = screen_recorder.get_status()
        audio_status = "Recording" if audio_recorder._recording else "Idle"
        return f"Screen: {screen}\nAudio: {audio_status}"
    elif action == "list":
        return list_recordings()
    return f"Unknown recording action: {action}. Available: start_screen, stop_screen, start_audio, stop_audio, status, list"
