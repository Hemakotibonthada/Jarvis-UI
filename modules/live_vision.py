"""
Live Vision Module — Real-time camera capture, screen vision, continuous monitoring,
and visual understanding using webcam, screen capture, and AI analysis.
Works in offline mode with basic CV, and with OpenAI for deep understanding.
"""

import asyncio
import base64
import io
import json
import time
import threading
from pathlib import Path
from datetime import datetime
from core.logger import get_logger
import config

log = get_logger("live_vision")

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    from PIL import Image, ImageGrab
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from openai import AsyncOpenAI
    _vision_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY) if config.OPENAI_API_KEY else None
except Exception:
    _vision_client = None


class LiveCamera:
    """Webcam capture and management."""

    def __init__(self):
        self._cap = None
        self._running = False
        self._latest_frame = None
        self._frame_lock = threading.Lock()
        self._monitor_thread = None
        self._monitor_callback = None
        self._monitor_interval = 5  # seconds

    def open(self, camera_index: int = 0) -> str:
        """Open a webcam."""
        if not HAS_CV2:
            return "OpenCV (cv2) not installed. Run: pip install opencv-python"
        try:
            self._cap = cv2.VideoCapture(camera_index)
            if not self._cap.isOpened():
                return f"Could not open camera {camera_index}. Check if webcam is connected."
            w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            return f"Camera {camera_index} opened: {w}x{h}"
        except Exception as e:
            return f"Camera open error: {e}"

    def close(self) -> str:
        """Close the webcam."""
        self._running = False
        if self._cap and self._cap.isOpened():
            self._cap.release()
            self._cap = None
            return "Camera closed."
        return "No camera was open."

    def capture_frame(self) -> tuple:
        """Capture a single frame. Returns (success, image_bytes, shape)."""
        if not self._cap or not self._cap.isOpened():
            # Try auto-open
            if HAS_CV2:
                self._cap = cv2.VideoCapture(0)

        if not self._cap or not self._cap.isOpened():
            return False, None, None

        ret, frame = self._cap.read()
        if not ret:
            return False, None, None

        with self._frame_lock:
            self._latest_frame = frame.copy()

        # Encode to JPEG
        _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return True, buf.tobytes(), frame.shape

    def capture_to_file(self, filename: str = "") -> str:
        """Capture a frame and save to file."""
        if not filename:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = str(config.GENERATED_DIR / f"camera_{ts}.jpg")

        ok, img_bytes, shape = self.capture_frame()
        if not ok:
            return "Failed to capture from camera."

        Path(filename).write_bytes(img_bytes)
        return f"Captured from camera: {filename} ({shape[1]}x{shape[0]})"

    def capture_to_base64(self) -> tuple:
        """Capture a frame and return as base64 string."""
        ok, img_bytes, shape = self.capture_frame()
        if not ok:
            return False, ""
        return True, base64.b64encode(img_bytes).decode()

    def list_cameras(self) -> str:
        """List available camera devices."""
        if not HAS_CV2:
            return "OpenCV not installed."
        cameras = []
        for i in range(5):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cameras.append(f"  Camera {i}: {w}x{h}")
                cap.release()
        if not cameras:
            return "No cameras detected."
        return "Available cameras:\n" + "\n".join(cameras)


class ScreenCapture:
    """Screen capture utilities."""

    @staticmethod
    def capture_screen(region: tuple = None) -> tuple:
        """Capture the screen (or a region). Returns (success, image_bytes)."""
        if HAS_PIL:
            try:
                img = ImageGrab.grab(bbox=region)
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=85)
                return True, buf.getvalue()
            except Exception:
                pass

        # Fallback to pyautogui
        try:
            import pyautogui
            img = pyautogui.screenshot(region=region)
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=85)
            return True, buf.getvalue()
        except Exception:
            return False, None

    @staticmethod
    def capture_screen_base64(region: tuple = None) -> tuple:
        ok, img_bytes = ScreenCapture.capture_screen(region)
        if ok:
            return True, base64.b64encode(img_bytes).decode()
        return False, ""

    @staticmethod
    def save_screenshot(filename: str = "", region: tuple = None) -> str:
        if not filename:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = str(config.GENERATED_DIR / f"screen_{ts}.jpg")
        ok, img_bytes = ScreenCapture.capture_screen(region)
        if not ok:
            return "Failed to capture screen."
        Path(filename).write_bytes(img_bytes)
        return f"Screen captured: {filename}"


class VisionAnalyzer:
    """AI-powered image understanding."""

    @staticmethod
    async def analyze_base64(image_b64: str, question: str = "Describe what you see in detail.",
                              detail: str = "auto") -> str:
        """Analyze a base64-encoded image with AI."""
        if not _vision_client:
            return VisionAnalyzer._offline_analyze(image_b64)

        try:
            response = await _vision_client.chat.completions.create(
                model=config.OPENAI_VISION_MODEL,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}",
                            "detail": detail,
                        }},
                    ],
                }],
                max_tokens=1500,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Vision analysis error: {e}. Falling back to basic analysis.\n" + VisionAnalyzer._offline_analyze(image_b64)

    @staticmethod
    def _offline_analyze(image_b64: str) -> str:
        """Basic offline image analysis using OpenCV."""
        if not HAS_CV2:
            return "No vision capabilities available offline (install opencv-python)."

        import numpy as np
        img_data = base64.b64decode(image_b64)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return "Could not decode image."

        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Basic analysis
        brightness = float(gray.mean())
        contrast = float(gray.std())

        # Color distribution
        b_mean, g_mean, r_mean = [float(img[:, :, i].mean()) for i in range(3)]
        dominant = "red" if r_mean > g_mean and r_mean > b_mean else "green" if g_mean > b_mean else "blue"

        # Edge detection for complexity
        edges = cv2.Canny(gray, 50, 150)
        edge_density = float(edges.mean())
        complexity = "simple" if edge_density < 10 else "moderate" if edge_density < 30 else "complex"

        # Face detection
        face_count = 0
        try:
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            face_count = len(faces)
        except Exception:
            pass

        # Text detection (basic)
        has_text = edge_density > 20 and contrast > 50

        result = (
            f"Image Analysis (offline):\n"
            f"  Size: {w}x{h}\n"
            f"  Brightness: {brightness:.0f}/255 ({'dark' if brightness < 85 else 'medium' if brightness < 170 else 'bright'})\n"
            f"  Contrast: {contrast:.0f}\n"
            f"  Dominant color: {dominant} (R:{r_mean:.0f} G:{g_mean:.0f} B:{b_mean:.0f})\n"
            f"  Visual complexity: {complexity}\n"
            f"  Faces detected: {face_count}\n"
            f"  Likely contains text: {'yes' if has_text else 'no'}"
        )
        return result

    @staticmethod
    async def analyze_file(image_path: str, question: str = "Describe this image in detail.") -> str:
        """Analyze an image file."""
        p = Path(image_path).expanduser()
        if not p.exists():
            return f"Image not found: {p}"
        with open(p, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return await VisionAnalyzer.analyze_base64(b64, question)

    @staticmethod
    async def compare_images(image1_b64: str, image2_b64: str) -> str:
        """Compare two images and describe differences."""
        if not _vision_client:
            return "Image comparison requires AI vision (set OPENAI_API_KEY)."
        try:
            response = await _vision_client.chat.completions.create(
                model=config.OPENAI_VISION_MODEL,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Compare these two images. Describe the differences and similarities."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image1_b64}"}},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image2_b64}"}},
                    ],
                }],
                max_tokens=1500,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Comparison error: {e}"


class LiveVisionSystem:
    """Unified live vision system — camera + screen + AI."""

    def __init__(self):
        self.camera = LiveCamera()
        self.screen = ScreenCapture()
        self.analyzer = VisionAnalyzer()
        self._watching = False
        self._watch_thread = None
        self._watch_callback = None
        self._watch_interval = 10

    async def see(self, source: str = "screen", question: str = "What do you see? Describe everything.") -> str:
        """Take a look at the screen or camera and describe what's visible."""
        if source == "camera" or source == "webcam":
            ok, b64 = self.camera.capture_to_base64()
            if not ok:
                return "Cannot access camera. Is a webcam connected?"
            result = await self.analyzer.analyze_base64(b64, question)
            return f"[Camera View]\n{result}"
        else:
            ok, b64 = self.screen.capture_screen_base64()
            if not ok:
                return "Cannot capture screen."
            result = await self.analyzer.analyze_base64(b64, question)
            return f"[Screen View]\n{result}"

    async def see_and_answer(self, question: str, source: str = "screen") -> str:
        """Look at screen/camera and answer a specific question about what's visible."""
        return await self.see(source, question)

    async def read_screen(self) -> str:
        """Read text visible on the screen."""
        return await self.see("screen", "Read all the text visible on this screen. Return the text content exactly as shown.")

    async def what_app_is_open(self) -> str:
        """Identify what application is currently in the foreground."""
        return await self.see("screen", "What application or window is currently active on this screen? What is the user doing?")

    async def describe_camera(self) -> str:
        """Describe what the webcam sees."""
        return await self.see("camera", "Describe what you see through this camera in detail. Include people, objects, and the environment.")

    async def detect_objects_camera(self) -> str:
        """Detect objects visible in the camera."""
        return await self.see("camera", "List all objects you can identify in this image. Be specific about each object, its position, and color.")

    async def capture_and_save(self, source: str = "screen") -> str:
        """Capture from source and save to file, return path."""
        if source == "camera":
            return self.camera.capture_to_file()
        else:
            return self.screen.save_screenshot()

    async def analyze_image_file(self, path: str, question: str = "Describe this image.") -> str:
        """Analyze a saved image file."""
        return await self.analyzer.analyze_file(path, question)

    # ─── Continuous Watching ──────────────────────────────────
    def start_watching(self, source: str = "screen", interval: int = 10,
                       callback=None) -> str:
        """Start continuous visual monitoring."""
        if self._watching:
            return "Already watching."
        self._watching = True
        self._watch_interval = max(5, interval)
        self._watch_callback = callback

        def _watch_loop():
            while self._watching:
                try:
                    if source == "camera":
                        ok, b64 = self.camera.capture_to_base64()
                    else:
                        ok, b64 = self.screen.capture_screen_base64()

                    if ok and self._watch_callback:
                        self._watch_callback(b64, source)
                except Exception as e:
                    log.error(f"Watch error: {e}")
                time.sleep(self._watch_interval)

        self._watch_thread = threading.Thread(target=_watch_loop, daemon=True, name="vision-watch")
        self._watch_thread.start()
        return f"Watching {source} every {self._watch_interval}s."

    def stop_watching(self) -> str:
        if not self._watching:
            return "Not watching."
        self._watching = False
        return "Stopped watching."

    # ─── Unified Interface ────────────────────────────────────
    async def vision_operation(self, operation: str, **kwargs) -> str:
        """Unified live vision interface."""
        source = kwargs.get("source", "screen")
        question = kwargs.get("question", "Describe what you see in detail.")

        ops = {
            "see": lambda: self.see(source, question),
            "screen": lambda: self.see("screen", question),
            "camera": lambda: self.see("camera", question),
            "read_screen": lambda: self.read_screen(),
            "what_app": lambda: self.what_app_is_open(),
            "describe_camera": lambda: self.describe_camera(),
            "detect_objects": lambda: self.detect_objects_camera(),
            "capture": lambda: self.capture_and_save(source),
            "analyze_file": lambda: self.analyze_image_file(kwargs.get("path", ""), question),
        }

        sync_ops = {
            "list_cameras": lambda: self.camera.list_cameras(),
            "open_camera": lambda: self.camera.open(int(kwargs.get("camera_index", 0))),
            "close_camera": lambda: self.camera.close(),
            "start_watch": lambda: self.start_watching(source, int(kwargs.get("interval", 10))),
            "stop_watch": lambda: self.stop_watching(),
        }

        if operation in ops:
            return await ops[operation]()
        if operation in sync_ops:
            return sync_ops[operation]()

        all_ops = list(ops.keys()) + list(sync_ops.keys())
        return f"Unknown vision operation: {operation}. Available: {', '.join(all_ops)}"


# ─── Singleton ────────────────────────────────────────────────
live_vision = LiveVisionSystem()
