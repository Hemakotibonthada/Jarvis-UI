"""
Streaming Processor — Listen and process audio in real-time chunks.
Processes speech incrementally without waiting for the user to finish speaking.
"""

import asyncio
import threading
import queue
import time
from datetime import datetime
from core.logger import get_logger
import config

log = get_logger("streaming")

try:
    import speech_recognition as sr
    HAS_SR = True
except ImportError:
    HAS_SR = False


class StreamingListener:
    """
    Listens to microphone continuously and processes speech in chunks.
    Instead of waiting for the user to stop speaking, it processes
    partial results and builds understanding incrementally.
    """

    def __init__(self):
        self._running = False
        self._thread = None
        self._chunk_queue = queue.Queue()
        self._on_partial = None   # callback(partial_text) — called as words come in
        self._on_complete = None  # callback(full_text) — called when user stops
        self._on_processing = None  # callback(text) — called when processing starts
        self.recognizer = sr.Recognizer() if HAS_SR else None
        self.stt_language = config.STT_LANGUAGE
        self._partial_text = ""
        self._silence_timeout = 2.0  # seconds of silence = end of utterance
        self._min_phrase = 0.5  # minimum seconds for a phrase

    def start(self, on_partial=None, on_complete=None) -> str:
        """Start streaming listener."""
        if not HAS_SR:
            return "SpeechRecognition not installed."
        if self._running:
            return "Already listening."

        self._running = True
        self._on_partial = on_partial
        self._on_complete = on_complete
        self._partial_text = ""

        self._thread = threading.Thread(
            target=self._listen_loop, daemon=True, name="stream-listener"
        )
        self._thread.start()
        return "Streaming listener started — speak naturally."

    def stop(self) -> str:
        """Stop streaming listener."""
        if not self._running:
            return "Not listening."
        self._running = False
        if self._partial_text and self._on_complete:
            self._on_complete(self._partial_text)
        self._partial_text = ""
        return "Streaming listener stopped."

    def _listen_loop(self):
        """Main listening loop with chunked processing."""
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                log.info("Streaming listener active")

                while self._running:
                    try:
                        # Listen for a short chunk
                        audio = self.recognizer.listen(
                            source,
                            timeout=3,
                            phrase_time_limit=5,
                        )

                        # Process in background to not block listening
                        threading.Thread(
                            target=self._process_chunk,
                            args=(audio,),
                            daemon=True,
                        ).start()

                    except sr.WaitTimeoutError:
                        # Silence — if we have accumulated text, finalize it
                        if self._partial_text:
                            final = self._partial_text.strip()
                            self._partial_text = ""
                            if final and self._on_complete:
                                self._on_complete(final)
                        continue
                    except Exception as e:
                        log.error(f"Stream listen error: {e}")
                        continue

        except Exception as e:
            log.error(f"Streaming listener error: {e}")
        finally:
            self._running = False
            log.info("Streaming listener stopped")

    def _process_chunk(self, audio):
        """Process a single audio chunk."""
        try:
            text = self.recognizer.recognize_google(
                audio,
                language=self.stt_language,
            )
            if text.strip():
                self._partial_text += " " + text.strip()

                if self._on_partial:
                    self._on_partial(text.strip())

        except sr.UnknownValueError:
            pass  # Couldn't understand — silence or noise
        except sr.RequestError as e:
            log.error(f"STT request error: {e}")

    @property
    def is_listening(self) -> bool:
        return self._running

    @property
    def current_text(self) -> str:
        return self._partial_text.strip()


class StreamingProcessor:
    """
    Combines streaming listening with incremental processing.
    Shows partial transcription in real-time while building the full command.
    """

    def __init__(self):
        self.listener = StreamingListener()
        self._brain = None
        self._broadcast = None
        self._processing = False

    def set_brain(self, brain, broadcast_fn):
        """Connect to the Jarvis brain and broadcast function."""
        self._brain = brain
        self._broadcast = broadcast_fn

    async def start_streaming(self) -> str:
        """Start streaming speech-to-action pipeline."""
        if self.listener.is_listening:
            return "Already streaming."

        def on_partial(text):
            """Called for each partial chunk of speech."""
            if self._broadcast:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.run_coroutine_threadsafe(
                            self._broadcast(json.dumps({
                                "type": "partial_speech",
                                "text": text,
                                "accumulated": self.listener.current_text,
                            })),
                            loop,
                        )
                except Exception:
                    pass

        def on_complete(text):
            """Called when user finishes speaking (silence detected)."""
            if self._brain and self._broadcast and not self._processing:
                self._processing = True
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.run_coroutine_threadsafe(
                            self._process_complete(text),
                            loop,
                        )
                except Exception:
                    self._processing = False

        result = self.listener.start(on_partial=on_partial, on_complete=on_complete)
        return result

    async def _process_complete(self, text: str):
        """Process completed speech through brain."""
        try:
            if self._broadcast:
                await self._broadcast(json.dumps({
                    "type": "voice_detected",
                    "message": text,
                }))
                await self._broadcast(json.dumps({
                    "type": "thinking",
                    "message": "Processing...",
                }))

            reply = await self._brain.think(text, broadcast=self._broadcast)

            if self._broadcast:
                await self._broadcast(json.dumps({
                    "type": "response",
                    "message": reply,
                }))
        except Exception as e:
            log.error(f"Stream processing error: {e}")
        finally:
            self._processing = False

    def stop_streaming(self) -> str:
        return self.listener.stop()

    def get_status(self) -> dict:
        return {
            "listening": self.listener.is_listening,
            "processing": self._processing,
            "current_text": self.listener.current_text,
        }


import json

# ─── Singleton ────────────────────────────────────────────────
streaming_processor = StreamingProcessor()
