"""
ESP32 IoT Module — Serial and MQTT communication with ESP32 boards.
Handles sensor reading (temperature, humidity) and device control.
"""

import json
import asyncio
import config

try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

try:
    import paho.mqtt.client as mqtt
    HAS_MQTT = True
except ImportError:
    HAS_MQTT = False


class ESP32Controller:
    """Manages communication with ESP32 boards via Serial and MQTT."""

    def __init__(self):
        self.serial_conn = None
        self.mqtt_client = None
        self.last_sensor_data = {}
        self._mqtt_connected = False

    # ─── Serial Communication ─────────────────────────────────
    def connect_serial(self, port: str = None, baud: int = None) -> str:
        if not HAS_SERIAL:
            return "pyserial not installed. Run: pip install pyserial"
        port = port or config.ESP32_SERIAL_PORT
        baud = baud or config.ESP32_BAUD_RATE
        try:
            self.serial_conn = serial.Serial(port, baud, timeout=2)
            return f"Connected to ESP32 on {port} at {baud} baud."
        except serial.SerialException as e:
            return f"Serial connection failed: {e}"

    def disconnect_serial(self):
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()

    def send_serial(self, data: str) -> str:
        if not self.serial_conn or not self.serial_conn.is_open:
            return "Not connected via serial. Call connect_serial() first."
        try:
            self.serial_conn.write((data + "\n").encode())
            response = self.serial_conn.readline().decode().strip()
            return response or "(no response)"
        except Exception as e:
            return f"Serial error: {e}"

    def list_serial_ports(self) -> str:
        if not HAS_SERIAL:
            return "pyserial not installed."
        ports = serial.tools.list_ports.comports()
        if not ports:
            return "No serial ports found."
        lines = [f"  {p.device} — {p.description}" for p in ports]
        return "Available serial ports:\n" + "\n".join(lines)

    # ─── MQTT Communication ───────────────────────────────────
    def connect_mqtt(self, broker: str = None, port: int = None) -> str:
        if not HAS_MQTT:
            return "paho-mqtt not installed. Run: pip install paho-mqtt"
        broker = broker or config.MQTT_BROKER
        port = port or config.MQTT_PORT
        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_message = self._on_mqtt_message
            self.mqtt_client.connect(broker, port)
            self.mqtt_client.loop_start()
            return f"Connecting to MQTT broker {broker}:{port}..."
        except Exception as e:
            return f"MQTT connection failed: {e}"

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        self._mqtt_connected = True
        client.subscribe(f"{config.MQTT_TOPIC_PREFIX}/sensors/#")
        client.subscribe(f"{config.MQTT_TOPIC_PREFIX}/status")

    def _on_mqtt_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            topic = msg.topic.split("/")[-1]
            self.last_sensor_data[topic] = payload
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    def publish_mqtt(self, topic: str, data: dict) -> str:
        if not self.mqtt_client or not self._mqtt_connected:
            return "MQTT not connected."
        try:
            self.mqtt_client.publish(
                f"{config.MQTT_TOPIC_PREFIX}/{topic}",
                json.dumps(data),
            )
            return f"Published to {topic}: {data}"
        except Exception as e:
            return f"MQTT publish error: {e}"

    # ─── High-Level APIs ──────────────────────────────────────
    def esp32_read_sensors(self) -> str:
        """Read temperature and humidity from ESP32."""
        # Try serial first
        if self.serial_conn and self.serial_conn.is_open:
            response = self.send_serial("READ_SENSORS")
            try:
                data = json.loads(response)
                self.last_sensor_data.update(data)
                return f"Temperature: {data.get('temperature', 'N/A')}°C, Humidity: {data.get('humidity', 'N/A')}%"
            except json.JSONDecodeError:
                return f"Raw sensor data: {response}"

        # Try MQTT cache
        if self.last_sensor_data:
            parts = []
            if "temperature" in self.last_sensor_data:
                parts.append(f"Temperature: {self.last_sensor_data['temperature']}°C")
            if "humidity" in self.last_sensor_data:
                parts.append(f"Humidity: {self.last_sensor_data['humidity']}%")
            if "dht" in self.last_sensor_data:
                d = self.last_sensor_data["dht"]
                parts.append(f"Temperature: {d.get('temperature', 'N/A')}°C, Humidity: {d.get('humidity', 'N/A')}%")
            return ", ".join(parts) if parts else "Sensor data: " + str(self.last_sensor_data)

        return "ESP32 not connected. Connect via serial (connect_serial) or MQTT (connect_mqtt) first."

    def esp32_control(self, command: str, params: dict = None) -> str:
        """Send a control command to ESP32."""
        params = params or {}
        cmd_data = json.dumps({"cmd": command, **params})

        # Try serial
        if self.serial_conn and self.serial_conn.is_open:
            return self.send_serial(cmd_data)

        # Try MQTT
        if self.mqtt_client and self._mqtt_connected:
            return self.publish_mqtt("control", {"cmd": command, **params})

        return "ESP32 not connected."


# Singleton instance
esp32 = ESP32Controller()
