"""
J.A.R.V.I.S. Voice Engine — Text-to-Speech and Speech-to-Text.
Uses Edge-TTS for human-like voice, SpeechRecognition for input,
and wake word detection.
"""

import asyncio
import io
import tempfile
import os
import edge_tts
import speech_recognition as sr
import config

try:
    import pygame
    pygame.mixer.init()
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False


class VoiceEngine:
    """Handles TTS output and STT input with wake word support and Telugu."""

    # Language configs
    LANG_CONFIG = {
        "en": {"tts_voice": config.EDGE_TTS_VOICE, "stt_lang": "en-US", "label": "English"},
        "te": {"tts_voice": config.EDGE_TTS_VOICE_TELUGU, "stt_lang": "te-IN", "label": "Telugu"},
    }

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.tts_voice = config.EDGE_TTS_VOICE
        self.tts_voice_telugu = config.EDGE_TTS_VOICE_TELUGU
        self.stt_language = config.STT_LANGUAGE  # "en-US" or "te-IN"
        self.current_language = config.LANGUAGE   # "en" or "te"
        self._speaking = False
        self._listening = False
        self.wake_word = config.WAKE_WORD.lower()
        self.use_wake_word = config.USE_WAKE_WORD
        self._on_command = None
        self._on_wake = None
        self._pronunciation_variants: list[str] = []

    def set_language(self, lang: str) -> str:
        """Switch language: 'en' for English, 'te' for Telugu."""
        lang = lang.lower().strip()
        if lang in self.LANG_CONFIG:
            cfg = self.LANG_CONFIG[lang]
            self.current_language = lang
            self.tts_voice = cfg["tts_voice"]
            self.stt_language = cfg["stt_lang"]
            return f"Language switched to {cfg['label']}. TTS: {cfg['tts_voice']}, STT: {cfg['stt_lang']}"
        return f"Unknown language: {lang}. Available: en (English), te (Telugu)"

    def get_language(self) -> dict:
        """Get current language settings."""
        return {
            "language": self.current_language,
            "label": self.LANG_CONFIG.get(self.current_language, {}).get("label", "Unknown"),
            "tts_voice": self.tts_voice,
            "stt_language": self.stt_language,
        }

    def load_voice_profile(self):
        """Load pronunciation variants from the trained voice profile."""
        try:
            from core.voice_enrollment import wake_trainer
            self._pronunciation_variants = wake_trainer.get_variants()
            if wake_trainer.profile.energy_threshold > 0:
                self.recognizer.energy_threshold = wake_trainer.profile.energy_threshold
        except Exception:
            self._pronunciation_variants = [self.wake_word]

    # ─── Text-to-Speech ───────────────────────────────────────
    async def speak(self, text: str, language: str = "") -> bytes:
        """Convert text to speech using Edge-TTS, return audio bytes and play."""
        self._speaking = True

        # Pick right voice for the language
        if language == "te" or (not language and self.current_language == "te"):
            tts_voice = self.tts_voice_telugu
        else:
            tts_voice = self.tts_voice

        # Limit TTS to reasonable length
        tts_text = text[:2000] if len(text) > 2000 else text
        communicate = edge_tts.Communicate(tts_text, tts_voice)
        audio_data = b""

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tmp_path = tmp.name
        tmp.close()

        try:
            await communicate.save(tmp_path)
            with open(tmp_path, "rb") as f:
                audio_data = f.read()

            if HAS_PYGAME:
                pygame.mixer.music.load(tmp_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    await asyncio.sleep(0.1)
        finally:
            self._speaking = False
            try:
                if HAS_PYGAME:
                    pygame.mixer.music.unload()
                os.unlink(tmp_path)
            except Exception:
                pass

        return audio_data

    async def speak_stream(self, text: str):
        """Stream TTS audio chunks (for WebSocket streaming)."""
        communicate = edge_tts.Communicate(text[:2000], self.tts_voice)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]

    def stop_speaking(self):
        """Interrupt current speech."""
        if HAS_PYGAME and self._speaking:
            pygame.mixer.music.stop()
            self._speaking = False

    # ─── Speech-to-Text ───────────────────────────────────────
    def listen(self, timeout: int = 5, phrase_limit: int = 15) -> str:
        """Listen to microphone and return recognized text."""
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_limit,
                )
                text = self.recognizer.recognize_google(audio, language=self.stt_language)
                return text.strip()
            except sr.WaitTimeoutError:
                return ""
            except sr.UnknownValueError:
                return ""
            except sr.RequestError as e:
                return f"[STT Error: {e}]"

    async def listen_async(self, timeout: int = 5) -> str:
        """Async wrapper around listen."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.listen, timeout)

    # ─── Wake Word Detection ─────────────────────────────────
    def _check_wake_word(self, text: str) -> tuple[bool, str]:
        """Check if text starts with wake word (or any trained variant) and strip it."""
        text_lower = text.lower().strip()

        # Check against all pronunciation variants learned during training
        variants = self._pronunciation_variants or [self.wake_word]

        matched_variant = ""
        for variant in variants:
            if text_lower.startswith(variant):
                matched_variant = variant
                break
            # Also check if variant appears as the first word
            first_word = text_lower.split()[0] if text_lower else ""
            if first_word == variant or self._is_close(first_word, variant):
                matched_variant = variant
                break

        if matched_variant:
            # Remove the matched variant from the command
            if text_lower.startswith(matched_variant):
                command = text[len(matched_variant):].strip()
            else:
                # Remove just the first word
                parts = text.split(None, 1)
                command = parts[1] if len(parts) > 1 else ""

            # Remove common filler words after wake word
            for prefix in [",", ".", "!", "?", "please", "can you", "could you"]:
                if command.lower().startswith(prefix):
                    command = command[len(prefix):].strip()
            return True, command

        return False, text

    @staticmethod
    def _is_close(a: str, b: str) -> bool:
        """Quick fuzzy check — within 2 char edits for words of similar length."""
        if abs(len(a) - len(b)) > 2:
            return False
        diffs = sum(1 for ca, cb in zip(a, b) if ca != cb) + abs(len(a) - len(b))
        return diffs <= 2

    def listen_with_wake_word(self, timeout: int = None) -> str:
        """
        Listen for wake word, then capture command.
        Returns the command text (without wake word).
        """
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            self._listening = True

            while self._listening:
                try:
                    audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=10)
                    text = self.recognizer.recognize_google(audio, language=self.stt_language)

                    if self.use_wake_word:
                        woke, command = self._check_wake_word(text)
                        if woke:
                            if self._on_wake:
                                self._on_wake()
                            if command:
                                return command
                            # Wake word detected but no command — listen for command
                            try:
                                audio2 = self.recognizer.listen(source, timeout=5, phrase_time_limit=15)
                                return self.recognizer.recognize_google(audio2, language=self.stt_language)
                            except (sr.WaitTimeoutError, sr.UnknownValueError):
                                continue
                    else:
                        return text.strip()

                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    continue
                except sr.RequestError:
                    continue

        return ""

    def listen_continuous(self, callback, use_wake_word: bool = True):
        """
        Continuously listen and call callback(text) for each utterance.
        Optionally uses wake word detection.
        Blocks the calling thread — run in a thread.
        """
        self._listening = True
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            while self._listening:
                try:
                    audio = self.recognizer.listen(source, phrase_time_limit=15)
                    text = self.recognizer.recognize_google(audio, language=self.stt_language)
                    if not text.strip():
                        continue

                    if use_wake_word and self.use_wake_word:
                        woke, command = self._check_wake_word(text)
                        if woke and command:
                            callback(command)
                        elif woke:
                            # Got wake word, listen for command
                            if self._on_wake:
                                self._on_wake()
                            try:
                                audio2 = self.recognizer.listen(source, timeout=5, phrase_time_limit=15)
                                cmd = self.recognizer.recognize_google(audio2, language=self.stt_language)
                                if cmd.strip():
                                    callback(cmd.strip())
                            except (sr.WaitTimeoutError, sr.UnknownValueError):
                                continue
                    else:
                        callback(text.strip())

                except (sr.UnknownValueError, sr.WaitTimeoutError):
                    continue
                except sr.RequestError:
                    continue

    def stop_listening(self):
        """Stop continuous listening."""
        self._listening = False

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    @property
    def is_listening(self) -> bool:
        return self._listening

    @staticmethod
    def list_microphones() -> list[str]:
        """List available microphone devices."""
        return sr.Microphone.list_microphone_names()

    def set_voice(self, voice_name: str):
        """Change the TTS voice."""
        self.tts_voice = voice_name

    @staticmethod
    async def list_voices() -> list[str]:
        """List available Edge-TTS voices."""
        voices = await edge_tts.list_voices()
        return [f"{v['ShortName']} ({v['Gender']}, {v['Locale']})" for v in voices]
