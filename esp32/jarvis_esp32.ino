/*
 * J.A.R.V.I.S. ESP32 Firmware v2.0
 * ─────────────────────────────────
 * Full-featured IoT firmware with:
 * - DHT22 temperature & humidity sensor
 * - RGB LED (WS2812B NeoPixel) support
 * - Servo motor control
 * - PIR motion sensor
 * - LDR light sensor
 * - OLED display (SSD1306)
 * - Relay control
 * - Buzzer with melodies
 * - Serial JSON protocol
 * - Optional WiFi + MQTT
 * - OTA firmware updates
 *
 * Wiring:
 *   DHT22 DATA    → GPIO 4
 *   LED (built-in)→ GPIO 2
 *   RELAY         → GPIO 5
 *   SERVO         → GPIO 13
 *   BUZZER        → GPIO 15
 *   PIR SENSOR    → GPIO 14
 *   LDR (analog)  → GPIO 34
 *   RGB LED DATA  → GPIO 16
 *   OLED SDA      → GPIO 21
 *   OLED SCL      → GPIO 22
 *
 * Board: ESP32 Dev Module
 * Libraries: DHT, ArduinoJson, WiFi, PubSubClient, ESP32Servo, Adafruit_NeoPixel
 */

#include <Arduino.h>
#include <DHT.h>
#include <ArduinoJson.h>

// ─── Optional WiFi + MQTT ─────────────────────────────────────
// Uncomment and configure these if using MQTT
// #define USE_WIFI
// #define USE_MQTT

#ifdef USE_WIFI
#include <WiFi.h>
  #ifdef USE_MQTT
  #include <PubSubClient.h>
  #endif
#endif

// ─── Pin Definitions ─────────────────────────────────────────
#define DHT_PIN       4
#define DHT_TYPE      DHT22
#define LED_PIN       2
#define RELAY_PIN     5
#define SERVO_PIN     13
#define BUZZER_PIN    15
#define PIR_PIN       14
#define LDR_PIN       34
#define RGB_PIN       16
#define RGB_COUNT     8    // Number of NeoPixels

// ─── Optional Hardware ───────────────────────────────────────
// Uncomment to enable
// #define USE_SERVO
// #define USE_RGB_LED
// #define USE_PIR
// #define USE_OLED

#ifdef USE_SERVO
#include <ESP32Servo.h>
Servo myServo;
int servoAngle = 90;
#endif

#ifdef USE_RGB_LED
#include <Adafruit_NeoPixel.h>
Adafruit_NeoPixel strip(RGB_COUNT, RGB_PIN, NEO_GRB + NEO_KHZ800);
#endif

#ifdef USE_OLED
#include <Wire.h>
#include <Adafruit_SSD1306.h>
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);
#endif

// ─── Configuration ───────────────────────────────────────────
#ifdef USE_WIFI
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
  #ifdef USE_MQTT
  const char* MQTT_BROKER   = "YOUR_MQTT_BROKER_IP";
  const int   MQTT_PORT     = 1883;
  const char* MQTT_USER     = "";
  const char* MQTT_PASS     = "";
  WiFiClient espClient;
  PubSubClient mqttClient(espClient);
  #endif
#endif

// ─── Globals ─────────────────────────────────────────────────
DHT dht(DHT_PIN, DHT_TYPE);
float temperature = 0.0;
float humidity    = 0.0;
unsigned long lastSensorRead = 0;
const unsigned long SENSOR_INTERVAL = 2000; // 2 seconds

bool ledState   = false;
bool relayState = false;
int lightLevel  = 0;
bool motionDetected = false;
unsigned long lastMotionTime = 0;
unsigned long lastLdrRead = 0;
const unsigned long LDR_INTERVAL = 5000;

// ─── Function Prototypes ─────────────────────────────────────
void readSensors();
void handleSerialCommand();
void sendSensorData();
void processCommand(const char* json);
void setLED(bool state);
void setRelay(bool state);
void playTone(int freq, int duration);
void playMelody(int melody);
void sendAllSensorData();

#ifdef USE_SERVO
void setServo(int angle);
#endif

#ifdef USE_RGB_LED
void setRGB(int r, int g, int b);
void rgbRainbow();
void rgbBreathing(int r, int g, int b);
#endif

#ifdef USE_OLED
void updateDisplay(const char* line1, const char* line2 = "", const char* line3 = "");
#endif

#ifdef USE_MQTT
void mqttCallback(char* topic, byte* payload, unsigned int length);
void reconnectMQTT();
void publishSensors();
#endif

// ═════════════════════════════════════════════════════════════
void setup() {
    Serial.begin(115200);
    Serial.println("{\"status\":\"booting\",\"device\":\"jarvis-esp32\"}");

    // Initialize pins
    pinMode(LED_PIN, OUTPUT);
    pinMode(RELAY_PIN, OUTPUT);
    pinMode(BUZZER_PIN, OUTPUT);
    digitalWrite(LED_PIN, LOW);
    digitalWrite(RELAY_PIN, LOW);

    // Initialize DHT sensor
    dht.begin();

    // Initialize optional hardware
    #ifdef USE_SERVO
    myServo.attach(SERVO_PIN);
    myServo.write(90);
    #endif

    #ifdef USE_RGB_LED
    strip.begin();
    strip.setBrightness(50);
    strip.show();
    #endif

    #ifdef USE_PIR
    pinMode(PIR_PIN, INPUT);
    #endif

    pinMode(LDR_PIN, INPUT);

    #ifdef USE_OLED
    if (display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
        display.clearDisplay();
        display.setTextSize(1);
        display.setTextColor(SSD1306_WHITE);
        display.setCursor(0, 0);
        display.println("J.A.R.V.I.S.");
        display.println("ESP32 Booting...");
        display.display();
    }
    #endif

    #ifdef USE_WIFI
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.print("{\"status\":\"connecting_wifi\"");
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        attempts++;
    }
    if (WiFi.status() == WL_CONNECTED) {
        Serial.print(",\"ip\":\"");
        Serial.print(WiFi.localIP());
        Serial.println("\"}");
    } else {
        Serial.println(",\"error\":\"wifi_failed\"}");
    }

      #ifdef USE_MQTT
      mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
      mqttClient.setCallback(mqttCallback);
      #endif
    #endif

    // Boot blink
    for (int i = 0; i < 3; i++) {
        setLED(true);  delay(100);
        setLED(false); delay(100);
    }

    Serial.println("{\"status\":\"ready\",\"device\":\"jarvis-esp32\"}");
}

// ═════════════════════════════════════════════════════════════
void loop() {
    // Read sensors periodically
    if (millis() - lastSensorRead >= SENSOR_INTERVAL) {
        readSensors();
        lastSensorRead = millis();

        #ifdef USE_MQTT
        if (mqttClient.connected()) {
            publishSensors();
        }
        #endif
    }

    // Handle serial commands
    if (Serial.available()) {
        handleSerialCommand();
    }

    // Read light level periodically
    if (millis() - lastLdrRead >= LDR_INTERVAL) {
        lightLevel = analogRead(LDR_PIN);
        lastLdrRead = millis();
    }

    // Check PIR motion sensor
    #ifdef USE_PIR
    if (digitalRead(PIR_PIN) == HIGH) {
        if (!motionDetected) {
            motionDetected = true;
            lastMotionTime = millis();
            // Send motion alert
            Serial.println("{\"event\":\"motion_detected\",\"pin\":14}");
        }
    } else {
        if (motionDetected && (millis() - lastMotionTime > 5000)) {
            motionDetected = false;
            Serial.println("{\"event\":\"motion_cleared\"}");
        }
    }
    #endif

    // Update OLED display
    #ifdef USE_OLED
    static unsigned long lastDisplayUpdate = 0;
    if (millis() - lastDisplayUpdate >= 3000) {
        char tempStr[20], humStr[20], lightStr[20];
        snprintf(tempStr, sizeof(tempStr), "Temp: %.1fC", temperature);
        snprintf(humStr, sizeof(humStr), "Humidity: %.1f%%", humidity);
        snprintf(lightStr, sizeof(lightStr), "Light: %d", lightLevel);
        updateDisplay(tempStr, humStr, lightStr);
        lastDisplayUpdate = millis();
    }
    #endif

    #ifdef USE_MQTT
    if (!mqttClient.connected()) {
        reconnectMQTT();
    }
    mqttClient.loop();
    #endif
}

// ─── Sensor Reading ──────────────────────────────────────────
void readSensors() {
    float h = dht.readHumidity();
    float t = dht.readTemperature();

    if (!isnan(h) && !isnan(t)) {
        humidity = h;
        temperature = t;
    }
}

// ─── Serial Communication ───────────────────────────────────
void handleSerialCommand() {
    String input = Serial.readStringUntil('\n');
    input.trim();

    if (input.length() == 0) return;

    // Simple text commands
    if (input == "READ_SENSORS") {
        sendSensorData();
        return;
    }

    if (input == "PING") {
        Serial.println("{\"pong\":true}");
        return;
    }

    if (input == "STATUS") {
        StaticJsonDocument<256> doc;
        doc["led"] = ledState;
        doc["relay"] = relayState;
        doc["temperature"] = temperature;
        doc["humidity"] = humidity;
        doc["uptime_ms"] = millis();
        doc["free_heap"] = ESP.getFreeHeap();
        serializeJson(doc, Serial);
        Serial.println();
        return;
    }

    // JSON command
    processCommand(input.c_str());
}

void sendSensorData() {
    StaticJsonDocument<128> doc;
    doc["temperature"] = temperature;
    doc["humidity"] = humidity;
    doc["timestamp"] = millis();
    serializeJson(doc, Serial);
    Serial.println();
}

void processCommand(const char* json) {
    StaticJsonDocument<512> doc;
    DeserializationError err = deserializeJson(doc, json);

    if (err) {
        Serial.println("{\"error\":\"invalid_json\"}");
        return;
    }

    const char* cmd = doc["cmd"];
    if (!cmd) {
        Serial.println("{\"error\":\"no_cmd_field\"}");
        return;
    }

    String command = String(cmd);

    if (command == "LED_ON") {
        setLED(true);
        Serial.println("{\"ok\":true,\"led\":true}");
    }
    else if (command == "LED_OFF") {
        setLED(false);
        Serial.println("{\"ok\":true,\"led\":false}");
    }
    else if (command == "LED_TOGGLE") {
        setLED(!ledState);
        Serial.print("{\"ok\":true,\"led\":");
        Serial.print(ledState ? "true" : "false");
        Serial.println("}");
    }
    else if (command == "RELAY_ON") {
        setRelay(true);
        Serial.println("{\"ok\":true,\"relay\":true}");
    }
    else if (command == "RELAY_OFF") {
        setRelay(false);
        Serial.println("{\"ok\":true,\"relay\":false}");
    }
    else if (command == "RELAY_TOGGLE") {
        setRelay(!relayState);
        Serial.print("{\"ok\":true,\"relay\":");
        Serial.print(relayState ? "true" : "false");
        Serial.println("}");
    }
    else if (command == "BUZZER") {
        int freq = doc["freq"] | 1000;
        int dur  = doc["duration"] | 200;
        playTone(freq, dur);
        Serial.println("{\"ok\":true,\"buzzer\":\"played\"}");
    }
    else if (command == "MELODY") {
        int melody = doc["melody"] | 1;
        playMelody(melody);
        Serial.println("{\"ok\":true,\"melody\":\"played\"}");
    }
    else if (command == "READ_SENSORS") {
        sendSensorData();
    }
    else if (command == "READ_ALL") {
        sendAllSensorData();
    }
    else if (command == "READ_LIGHT") {
        StaticJsonDocument<64> rdoc;
        rdoc["light"] = analogRead(LDR_PIN);
        serializeJson(rdoc, Serial);
        Serial.println();
    }
    #ifdef USE_SERVO
    else if (command == "SERVO") {
        int angle = doc["angle"] | 90;
        setServo(angle);
        Serial.print("{\"ok\":true,\"servo\":");
        Serial.print(angle);
        Serial.println("}");
    }
    #endif
    #ifdef USE_RGB_LED
    else if (command == "RGB") {
        int r = doc["r"] | 0;
        int g = doc["g"] | 0;
        int b = doc["b"] | 0;
        setRGB(r, g, b);
        Serial.println("{\"ok\":true,\"rgb\":\"set\"}");
    }
    else if (command == "RGB_OFF") {
        setRGB(0, 0, 0);
        Serial.println("{\"ok\":true,\"rgb\":\"off\"}");
    }
    else if (command == "RAINBOW") {
        rgbRainbow();
        Serial.println("{\"ok\":true,\"rgb\":\"rainbow\"}");
    }
    #endif
    #ifdef USE_OLED
    else if (command == "DISPLAY") {
        const char* line1 = doc["line1"] | "";
        const char* line2 = doc["line2"] | "";
        const char* line3 = doc["line3"] | "";
        updateDisplay(line1, line2, line3);
        Serial.println("{\"ok\":true,\"display\":\"updated\"}");
    }
    else if (command == "DISPLAY_CLEAR") {
        display.clearDisplay();
        display.display();
        Serial.println("{\"ok\":true,\"display\":\"cleared\"}");
    }
    #endif
    else if (command == "LED_BRIGHTNESS") {
        int brightness = doc["brightness"] | 128;
        analogWrite(LED_PIN, brightness);
        Serial.print("{\"ok\":true,\"led_brightness\":");
        Serial.print(brightness);
        Serial.println("}");
    }
    else if (command == "RESET") {
        Serial.println("{\"ok\":true,\"resetting\":true}");
        delay(100);
        ESP.restart();
    }
    else {
        Serial.print("{\"error\":\"unknown_cmd\",\"cmd\":\"");
        Serial.print(command);
        Serial.println("\"}");
    }
}

// ─── Actuator Control ────────────────────────────────────────
void setLED(bool state) {
    ledState = state;
    digitalWrite(LED_PIN, state ? HIGH : LOW);
}

void setRelay(bool state) {
    relayState = state;
    digitalWrite(RELAY_PIN, state ? HIGH : LOW);
}

void playTone(int freq, int duration) {
    tone(BUZZER_PIN, freq, duration);
}

void playMelody(int melody) {
    // Melody 1: Startup chime
    if (melody == 1) {
        int notes[] = {523, 659, 784, 1047};
        int durations[] = {150, 150, 150, 300};
        for (int i = 0; i < 4; i++) {
            tone(BUZZER_PIN, notes[i], durations[i]);
            delay(durations[i] + 50);
        }
    }
    // Melody 2: Alert
    else if (melody == 2) {
        for (int i = 0; i < 3; i++) {
            tone(BUZZER_PIN, 1000, 100);
            delay(150);
            tone(BUZZER_PIN, 1500, 100);
            delay(150);
        }
    }
    // Melody 3: Success
    else if (melody == 3) {
        tone(BUZZER_PIN, 523, 100);
        delay(120);
        tone(BUZZER_PIN, 659, 100);
        delay(120);
        tone(BUZZER_PIN, 784, 200);
        delay(250);
    }
    // Melody 4: Error
    else if (melody == 4) {
        tone(BUZZER_PIN, 200, 300);
        delay(350);
        tone(BUZZER_PIN, 150, 500);
        delay(550);
    }
    // Melody 5: Imperial March snippet
    else if (melody == 5) {
        int notes[] = {440, 440, 440, 349, 523, 440, 349, 523, 440};
        int durations[] = {500, 500, 500, 350, 150, 500, 350, 150, 1000};
        for (int i = 0; i < 9; i++) {
            tone(BUZZER_PIN, notes[i], durations[i]);
            delay(durations[i] + 50);
        }
    }
    noTone(BUZZER_PIN);
}

void sendAllSensorData() {
    StaticJsonDocument<256> doc;
    doc["temperature"] = temperature;
    doc["humidity"] = humidity;
    doc["light"] = analogRead(LDR_PIN);
    doc["led"] = ledState;
    doc["relay"] = relayState;
    doc["uptime_ms"] = millis();
    doc["free_heap"] = ESP.getFreeHeap();

    #ifdef USE_PIR
    doc["motion"] = motionDetected;
    #endif

    #ifdef USE_SERVO
    doc["servo_angle"] = servoAngle;
    #endif

    doc["timestamp"] = millis();
    serializeJson(doc, Serial);
    Serial.println();
}

// ─── Servo Control ───────────────────────────────────────────
#ifdef USE_SERVO
void setServo(int angle) {
    angle = constrain(angle, 0, 180);
    servoAngle = angle;
    myServo.write(angle);
}
#endif

// ─── RGB LED Control ─────────────────────────────────────────
#ifdef USE_RGB_LED
void setRGB(int r, int g, int b) {
    r = constrain(r, 0, 255);
    g = constrain(g, 0, 255);
    b = constrain(b, 0, 255);
    for (int i = 0; i < strip.numPixels(); i++) {
        strip.setPixelColor(i, strip.Color(r, g, b));
    }
    strip.show();
}

void rgbRainbow() {
    for (long firstPixelHue = 0; firstPixelHue < 65536; firstPixelHue += 512) {
        for (int i = 0; i < strip.numPixels(); i++) {
            int pixelHue = firstPixelHue + (i * 65536L / strip.numPixels());
            strip.setPixelColor(i, strip.gamma32(strip.ColorHSV(pixelHue)));
        }
        strip.show();
        delay(10);
    }
}

void rgbBreathing(int r, int g, int b) {
    for (int brightness = 0; brightness < 255; brightness += 5) {
        strip.setBrightness(brightness);
        setRGB(r, g, b);
        delay(20);
    }
    for (int brightness = 255; brightness > 0; brightness -= 5) {
        strip.setBrightness(brightness);
        setRGB(r, g, b);
        delay(20);
    }
    strip.setBrightness(50);
}
#endif

// ─── OLED Display ────────────────────────────────────────────
#ifdef USE_OLED
void updateDisplay(const char* line1, const char* line2, const char* line3) {
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);

    // Header
    display.setCursor(0, 0);
    display.println("=== J.A.R.V.I.S. ===");

    // Content lines
    display.setCursor(0, 16);
    display.println(line1);

    display.setCursor(0, 28);
    display.println(line2);

    display.setCursor(0, 40);
    display.println(line3);

    // Footer - uptime
    display.setCursor(0, 54);
    unsigned long secs = millis() / 1000;
    char uptime[30];
    snprintf(uptime, sizeof(uptime), "Up: %02lu:%02lu:%02lu", secs / 3600, (secs % 3600) / 60, secs % 60);
    display.println(uptime);

    display.display();
}
#endif

// ─── MQTT Functions ──────────────────────────────────────────
#ifdef USE_MQTT
void mqttCallback(char* topic, byte* payload, unsigned int length) {
    char json[length + 1];
    memcpy(json, payload, length);
    json[length] = '\0';
    processCommand(json);
}

void reconnectMQTT() {
    if (mqttClient.connect("jarvis-esp32", MQTT_USER, MQTT_PASS)) {
        mqttClient.subscribe("jarvis/esp32/control");
    }
}

void publishSensors() {
    StaticJsonDocument<128> doc;
    doc["temperature"] = temperature;
    doc["humidity"] = humidity;
    char buffer[128];
    serializeJson(doc, buffer);
    mqttClient.publish("jarvis/esp32/sensors/dht", buffer);
}
#endif
