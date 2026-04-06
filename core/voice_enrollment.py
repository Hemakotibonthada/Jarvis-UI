"""
Voice Enrollment Module — First-time wake word training.
Records the user saying the wake word multiple times, captures how Google STT
interprets their pronunciation, and stores variants for improved matching.
Also calibrates microphone energy thresholds for the user's environment.
"""

import json
import time
import statistics
from pathlib import Path
from datetime import datetime
import speech_recognition as sr
from core.logger import get_logger
import config

log = get_logger("enrollment")

VOICE_PROFILE_FILE = config.DATA_DIR / "voice_profile.json"

# Number of samples to collect during training
TRAINING_SAMPLES = 3


class VoiceProfile:
    """Stores the user's voice profile and wake word pronunciation data."""

    def __init__(self):
        self.enrolled = False
        self.user_name = ""
        self.wake_word = config.WAKE_WORD.lower()
        self.pronunciation_variants: list[str] = []  # How STT heard the user
        self.energy_threshold = 300
        self.ambient_noise_level = 0.0
        self.enrollment_date = ""
        self.samples_collected = 0
        self.confidence_scores: list[float] = []
        self.avg_phrase_duration = 0.0

    def to_dict(self) -> dict:
        return {
            "enrolled": self.enrolled,
            "user_name": self.user_name,
            "wake_word": self.wake_word,
            "pronunciation_variants": self.pronunciation_variants,
            "energy_threshold": self.energy_threshold,
            "ambient_noise_level": self.ambient_noise_level,
            "enrollment_date": self.enrollment_date,
            "samples_collected": self.samples_collected,
            "confidence_scores": self.confidence_scores,
            "avg_phrase_duration": self.avg_phrase_duration,
        }

    @staticmethod
    def from_dict(data: dict) -> 'VoiceProfile':
        p = VoiceProfile()
        for k, v in data.items():
            if hasattr(p, k):
                setattr(p, k, v)
        return p

    def save(self):
        VOICE_PROFILE_FILE.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @staticmethod
    def load() -> 'VoiceProfile':
        if VOICE_PROFILE_FILE.exists():
            try:
                data = json.loads(VOICE_PROFILE_FILE.read_text(encoding="utf-8"))
                return VoiceProfile.from_dict(data)
            except (json.JSONDecodeError, OSError):
                pass
        return VoiceProfile()


class WakeWordTrainer:
    """
    Trains the wake word by having the user say it multiple times.
    Captures Google STT's interpretation of the pronunciation and
    stores all variants for fuzzy matching.
    """

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.profile = VoiceProfile.load()
        self._training_active = False
        self._current_step = 0
        self._samples: list[dict] = []

    @property
    def is_enrolled(self) -> bool:
        return self.profile.enrolled

    @property
    def is_training(self) -> bool:
        return self._training_active

    def get_status(self) -> dict:
        return {
            "enrolled": self.profile.enrolled,
            "training_active": self._training_active,
            "current_step": self._current_step,
            "total_steps": TRAINING_SAMPLES,
            "variants": self.profile.pronunciation_variants,
            "user_name": self.profile.user_name,
            "enrollment_date": self.profile.enrollment_date,
        }

    def start_training(self) -> dict:
        """Begin the training session."""
        self._training_active = True
        self._current_step = 0
        self._samples = []
        log.info("Wake word training started")
        return {
            "status": "training_started",
            "step": 0,
            "total": TRAINING_SAMPLES,
            "message": (
                f"Let's train your wake word. I'll ask you to say "
                f"'{config.WAKE_WORD}' {TRAINING_SAMPLES} times so I can learn "
                f"your pronunciation. First, let me calibrate your microphone..."
            ),
        }

    def calibrate_mic(self) -> dict:
        """
        Step 0: Calibrate microphone — measure ambient noise.
        Returns the ambient noise level detected.
        """
        try:
            with sr.Microphone() as source:
                log.info("Calibrating microphone...")
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                ambient = self.recognizer.energy_threshold
                self.profile.ambient_noise_level = ambient
                self.profile.energy_threshold = ambient
                log.info(f"Ambient noise level: {ambient:.0f}")

                return {
                    "status": "calibrated",
                    "ambient_noise": round(ambient, 1),
                    "message": (
                        f"Microphone calibrated. Ambient noise level: {ambient:.0f}. "
                        f"Now, please say '{config.WAKE_WORD}' clearly when prompted."
                    ),
                    "next_step": 1,
                }
        except OSError as e:
            return {
                "status": "error",
                "message": f"Microphone not accessible: {e}. Check your audio input device.",
            }

    def record_sample(self, sample_number: int) -> dict:
        """
        Record one pronunciation sample of the wake word.
        Returns what the STT heard.
        """
        if not self._training_active:
            return {"status": "error", "message": "Training not started."}

        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                self.recognizer.energy_threshold = max(
                    self.profile.energy_threshold * 0.8, 200
                )

                log.info(f"Recording sample {sample_number}/{TRAINING_SAMPLES}...")
                start_time = time.time()

                audio = self.recognizer.listen(
                    source, timeout=8, phrase_time_limit=5
                )

                duration = time.time() - start_time

                # Try to recognize what the user said
                try:
                    # Get multiple alternatives from Google
                    result = self.recognizer.recognize_google(
                        audio, show_all=True
                    )

                    if not result or not isinstance(result, dict):
                        return {
                            "status": "retry",
                            "step": sample_number,
                            "message": (
                                "I couldn't hear anything. Please speak louder and "
                                f"say '{config.WAKE_WORD}' clearly."
                            ),
                        }

                    alternatives = result.get("alternative", [])
                    if not alternatives:
                        return {
                            "status": "retry",
                            "step": sample_number,
                            "message": "No speech detected. Please try again.",
                        }

                    # Extract all interpretations
                    heard_texts = []
                    confidence = 0.0
                    for alt in alternatives[:5]:
                        text = alt.get("transcript", "").strip().lower()
                        conf = alt.get("confidence", 0.0)
                        if text:
                            heard_texts.append(text)
                            if conf > confidence:
                                confidence = conf

                    primary = heard_texts[0] if heard_texts else ""

                    # Store sample
                    sample = {
                        "number": sample_number,
                        "primary": primary,
                        "alternatives": heard_texts,
                        "confidence": confidence,
                        "duration": round(duration, 2),
                        "timestamp": datetime.now().isoformat(),
                    }
                    self._samples.append(sample)
                    self._current_step = sample_number

                    log.info(
                        f"Sample {sample_number}: heard '{primary}' "
                        f"(confidence: {confidence:.2f}, alternatives: {heard_texts})"
                    )

                    return {
                        "status": "recorded",
                        "step": sample_number,
                        "total": TRAINING_SAMPLES,
                        "heard": primary,
                        "alternatives": heard_texts[:3],
                        "confidence": round(confidence, 2),
                        "duration": round(duration, 2),
                        "message": (
                            f"Got it! I heard: '{primary}'"
                            + (
                                f" (and also: {', '.join(heard_texts[1:3])})"
                                if len(heard_texts) > 1
                                else ""
                            )
                        ),
                        "done": sample_number >= TRAINING_SAMPLES,
                    }

                except sr.UnknownValueError:
                    return {
                        "status": "retry",
                        "step": sample_number,
                        "message": (
                            "I couldn't understand that. Please speak clearly "
                            f"and say '{config.WAKE_WORD}'."
                        ),
                    }
                except sr.RequestError as e:
                    return {
                        "status": "error",
                        "message": f"Speech recognition service error: {e}",
                    }

        except sr.WaitTimeoutError:
            return {
                "status": "retry",
                "step": sample_number,
                "message": "Timed out waiting for speech. Please try again.",
            }
        except OSError as e:
            return {
                "status": "error",
                "message": f"Microphone error: {e}",
            }

    def finish_training(self, user_name: str = "") -> dict:
        """
        Finalize training — build pronunciation variant list from samples.
        """
        if not self._samples:
            return {
                "status": "error",
                "message": "No samples recorded. Please complete the training first.",
            }

        self._training_active = False

        # Collect all pronunciation variants heard by STT
        all_variants = set()
        confidences = []
        durations = []

        for sample in self._samples:
            # Add primary interpretation
            all_variants.add(sample["primary"])
            # Add alternatives
            for alt in sample.get("alternatives", []):
                all_variants.add(alt)
            if sample.get("confidence"):
                confidences.append(sample["confidence"])
            if sample.get("duration"):
                durations.append(sample["duration"])

        # Always include the canonical wake word itself
        all_variants.add(config.WAKE_WORD.lower())

        # Common misheard variants of "jarvis"
        common_variants = [
            "jarvis", "jarves", "jervis", "jarvas", "jarvice",
            "jarves", "javis", "gervis", "jarbs", "jarv",
            "service", "nervous", "harvest",
        ]
        # Only add common ones if they're close to what was heard
        for cv in common_variants:
            for heard in list(all_variants):
                if _fuzzy_match(cv, heard):
                    all_variants.add(cv)

        variants_list = sorted(all_variants)

        # Build profile
        self.profile.enrolled = True
        self.profile.user_name = user_name or self.profile.user_name
        self.profile.wake_word = config.WAKE_WORD.lower()
        self.profile.pronunciation_variants = variants_list
        self.profile.enrollment_date = datetime.now().isoformat()
        self.profile.samples_collected = len(self._samples)
        self.profile.confidence_scores = confidences
        if durations:
            self.profile.avg_phrase_duration = round(
                statistics.mean(durations), 2
            )
        self.profile.save()

        log.info(
            f"Training complete. {len(variants_list)} pronunciation variants: "
            f"{variants_list}"
        )

        return {
            "status": "complete",
            "variants": variants_list,
            "samples": len(self._samples),
            "avg_confidence": (
                round(statistics.mean(confidences), 2) if confidences else 0
            ),
            "message": (
                f"Training complete! I've learned {len(variants_list)} ways "
                f"you might say '{config.WAKE_WORD}'. "
                + (f"Welcome, {user_name}!" if user_name else "")
                + " The wake word listener is now optimized for your voice."
            ),
        }

    def reset_profile(self) -> dict:
        """Reset the voice profile (re-enroll)."""
        self.profile = VoiceProfile()
        self.profile.save()
        self._samples = []
        self._training_active = False
        self._current_step = 0
        return {
            "status": "reset",
            "message": "Voice profile reset. You can re-train the wake word.",
        }

    def get_variants(self) -> list[str]:
        """Get all learned pronunciation variants for matching."""
        if self.profile.pronunciation_variants:
            return self.profile.pronunciation_variants
        return [config.WAKE_WORD.lower()]


def _fuzzy_match(a: str, b: str) -> bool:
    """Simple fuzzy match — checks if two strings are similar enough."""
    a, b = a.lower(), b.lower()
    if a == b:
        return True
    if a in b or b in a:
        return True
    # Levenshtein-ish: allow up to 2 char differences for short words
    if abs(len(a) - len(b)) > 2:
        return False
    diffs = sum(1 for ca, cb in zip(a, b) if ca != cb)
    diffs += abs(len(a) - len(b))
    return diffs <= 2


# ─── Singleton ────────────────────────────────────────────────
wake_trainer = WakeWordTrainer()
