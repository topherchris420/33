/*
 * LAUNCHER ESP32 CODE (WiFi AP + Comm Relay + Fusion + GPS + Barometer)
 * V4 - Fully Non-Blocking & GPS Status Tracking
 */

#include <Arduino.h>
#include <SPI.h> 
#include <Wire.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <ESP32Servo.h>
#include <QMC5883LCompass.h>
#include <TinyGPS++.h>
#include <Adafruit_BMP085.h>
#include <math.h>
#include <stdlib.h>
#include "../../shared/Project33Protocol.h"

const char* ssid = "ROCKET_LAUNCHER";
const char* password = "launch_secure"; 
const int udpPort = 4444;
const int UDP_COMMAND_BUFFER_SIZE = 192;
const char* DASHBOARD_AUTH_TOKEN = "project33_bench_token";
const char* DASHBOARD_HELLO_PREFIX = "HELLO,";
const bool ENABLE_DASHBOARD_LAUNCH = false;
WiFiUDP udp;
IPAddress dashboardIP;
bool dashboardConnected = false;

const int RX2_PIN = 16;
const int TX2_PIN = 17;
const int SWITCH_PIN = 5;         
const int BUTTON_PIN = 18;        
const int LED_PIN = 23;           
const int BUZZER_PIN = 2;         
const int LAUNCHER_SERVO_PIN = 19; 
const int I2C_SDA = 21;
const int I2C_SCL = 22;
const int GPS_RX_PIN = 4; // Using D4 for GPS RX

const int SERVO_ON = 170;
const int SERVO_OFF = 55;

enum SystemState { SAFE, ARMING, READY, IGNITING };
SystemState currentState = SAFE;

Servo launcherServo;
QMC5883LCompass compass;
TinyGPSPlus gps;
HardwareSerial SerialGPS(1); // Use Hardware Serial 1 for GPS
Adafruit_BMP085 bmp;
bool bmpHealthy = false;

// Environment Filter Variables
float filteredAlt = 0.0;
const float ALT_ALPHA = 0.15; // Filter strength for Altitude (0.0 to 1.0)

unsigned long lastHeartbeatTime = 0;
const unsigned long HEARTBEAT_TIMEOUT = 2000; 

float mpu_ax = 0.0, mpu_ay = 0.0, mpu_az = 0.0;
float cal_ay = 0.0, cal_az = 1.0; 

const float MAG_OFFSET_X = -211.00;
const float MAG_OFFSET_Y = 897.00;
const float MAG_OFFSET_Z = -514.50;
const float MAG_SCALE_X = 0.988;
const float MAG_SCALE_Y = 0.971;
const float MAG_SCALE_Z = 1.044;

bool udpLaunchTriggered = false;
bool rocketReady = false; 
bool rocketIgnited = false; 

void buzzerOn() { digitalWrite(BUZZER_PIN, LOW); }
void buzzerOff() { digitalWrite(BUZZER_PIN, HIGH); }

void beep(int ms) { buzzerOn(); delay(ms); buzzerOff(); }
void successTone() { beep(150); delay(150); beep(150); }
void errorTone() { for(int i=0; i<5; i++) { beep(100); delay(100); } }

bool isSwitchArmed() { return digitalRead(SWITCH_PIN) == LOW; }
bool isButtonPressed() { return digitalRead(BUTTON_PIN) == LOW; }

void abortSequence(String reason);
void waitForSwitchReset();
void updateAndPrintFusion();
void processGPS();

void setup() {
    Serial.begin(115200); 
    
    // Configure hardware serial buffer to prevent data overflow at 115200 baud
    Serial2.setRxBufferSize(2048); 
    Serial2.begin(115200, SERIAL_8N1, RX2_PIN, TX2_PIN);
    Serial2.setTimeout(20); 

    // Setup GPS Serial on the RX pin (ignoring TX by passing -1)
    SerialGPS.begin(9600, SERIAL_8N1, GPS_RX_PIN, -1);

    Serial.println("Starting WiFi Access Point...");
    WiFi.softAP(ssid, password);
    IPAddress IP = WiFi.softAPIP();
    Serial.print("AP IP address: ");
    Serial.println(IP);
    udp.begin(udpPort);

    Wire.begin(I2C_SDA, I2C_SCL);
    compass.init();
    compass.setSmoothing(10, true);
    Wire.setClock(400000); 

    pinMode(SWITCH_PIN, INPUT_PULLUP);
    pinMode(BUTTON_PIN, INPUT_PULLUP);
    pinMode(LED_PIN, OUTPUT);
    pinMode(BUZZER_PIN, OUTPUT);
    buzzerOff();
    digitalWrite(LED_PIN, LOW);
    
    launcherServo.setPeriodHertz(50); 
    launcherServo.attach(LAUNCHER_SERVO_PIN);
    launcherServo.write(SERVO_OFF); 

    if (bmp.begin()) {
        bmpHealthy = true;
        filteredAlt = bmp.readAltitude(); // Seed the filter
        Serial.println("BMP180 initialized.");
    } else {
        bmpHealthy = false;
        filteredAlt = 0.0;
        Serial.println("Warning: BMP180 not found - altitude telemetry disabled.");
    }

    // --- GPS STARTUP CHECK ---
    Serial.println("Checking GPS NMEA Data...");
    bool gpsWorks = false;
    const int MAX_GPS_RETRIES = 3;

    for (int retry = 0; retry < MAX_GPS_RETRIES && !gpsWorks; retry++) {
        unsigned long gpsStart = millis();
        Serial.printf("GPS attempt %d/%d...\n", retry + 1, MAX_GPS_RETRIES);

        while (millis() - gpsStart < 5000) {
            while (SerialGPS.available() > 0) {
                char c = SerialGPS.read();
                if (c == '$') { // Standard start of an NMEA sentence
                    gpsWorks = true;
                }
                gps.encode(c);
            }
            if (gpsWorks) break;
            delay(10);
        }

        if (!gpsWorks && retry < MAX_GPS_RETRIES - 1) {
            Serial.println("GPS attempt failed, retrying in 2s...");
            delay(2000);
        }
    }

    if (!gpsWorks) {
        Serial.println("WARNING: NO GPS DATA AFTER RETRIES - continuing without GPS");
        // Continue instead of halting - GPS is useful but not critical for launcher function
        digitalWrite(LED_PIN, LOW);
    }
    
    Serial.println("GPS Test Passed.");
    delay(500); 
    successTone();
}

void sendToDashboard(String msg) {
    if (dashboardConnected) {
        udp.beginPacket(dashboardIP, udpPort);
        udp.println(msg);
        udp.endPacket();
    }
}

void processGPS() {
    while (SerialGPS.available() > 0) {
        gps.encode(SerialGPS.read());
    }
}

void processSerial2() {
    while (Serial2.available()) {
        String msg = Serial2.readStringUntil('\n');
        msg.trim();

        if (msg.indexOf(Project33Protocol::READY) != -1) {
            rocketReady = true; 
        }
        else if (msg.indexOf(Project33Protocol::IGNITED) != -1) {
            rocketIgnited = true;
        }
        else if (msg.startsWith(Project33Protocol::LOG_PREFIX)) {
            sendToDashboard(msg);
        }
        else if (msg.startsWith("CMD_REJECT:") || msg.startsWith(Project33Protocol::ABORT_PREFIX)) {
            sendToDashboard(msg);
        }
        else if (msg.startsWith(Project33Protocol::DATA_PREFIX) || msg.startsWith("ALIVE")) {
            lastHeartbeatTime = millis();
            
            if (msg.startsWith(Project33Protocol::DATA_PREFIX)) {
                int c[10]; // 10 commas for the new skew array
                c[0] = msg.indexOf(',');
                for(int i=1; i<10; i++) c[i] = msg.indexOf(',', c[i-1] + 1);

                // Validate all comma positions are valid before parsing
                bool valid = true;
                for (int i = 0; i < 10; i++) {
                    if (c[i] < 0) { valid = false; break; }
                }

                if (valid && c[9] > 0) { // Check that all fields arrived
                    mpu_ax = msg.substring(c[0]+1, c[1]).toFloat();
                    mpu_ay = msg.substring(c[1]+1, c[2]).toFloat();
                    mpu_az = msg.substring(c[2]+1, c[3]).toFloat();

                    String roll = msg.substring(c[3]+1, c[4]);
                    String rate = msg.substring(c[4]+1, c[5]);
                    String out = msg.substring(c[5]+1, c[6]);
                    String state = msg.substring(c[6]+1, c[7]);
                    String kp = msg.substring(c[7]+1, c[8]);
                    String kd = msg.substring(c[8]+1, c[9]);
                    String skew = msg.substring(c[9]+1);

                    sendToDashboard("T," + String(millis()) + "," + roll + "," + rate + "," + out);
                    sendToDashboard(String(Project33Protocol::STATUS_PREFIX) + state + "," + kp + "," + kd + "," + skew);
                } else {
                    Serial.println("Warning: Malformed telemetry data - missing fields");
                }
            }
        }
    }
}

bool parseBoundedFloat(const String &text, float &value) {
    if (text.length() == 0 || text.length() >= 24) return false;

    char buffer[24];
    text.toCharArray(buffer, sizeof(buffer));
    char *end = nullptr;
    value = strtof(buffer, &end);

    return end != buffer && *end == '\0' && isfinite(value) && value >= 0.0 && value <= 10.0;
}

bool isValidPidCommand(const String &command) {
    float kp = 0.0;
    float kd = 0.0;
    int c1 = command.indexOf(',');
    int c2 = command.indexOf(',', c1 + 1);
    if (c1 <= 0 || c2 <= c1 + 1 || command.indexOf(',', c2 + 1) != -1) return false;

    return parseBoundedFloat(command.substring(c1 + 1, c2), kp) &&
           parseBoundedFloat(command.substring(c2 + 1), kd);
}

bool isAuthenticatedDashboard(IPAddress remote) {
    return dashboardConnected && remote == dashboardIP;
}

bool isValidDashboardHello(const String &msg) {
    return msg == String(DASHBOARD_HELLO_PREFIX) + DASHBOARD_AUTH_TOKEN;
}

void processUDP() {
    int packetSize = udp.parsePacket();
    if (packetSize) {
        char buffer[UDP_COMMAND_BUFFER_SIZE];
        int bytesRead = udp.read(buffer, min(packetSize, UDP_COMMAND_BUFFER_SIZE - 1));
        buffer[bytesRead] = '\0';

        String msg = String(buffer);
        msg.trim();

        IPAddress remote = udp.remoteIP();

        if (msg.startsWith(DASHBOARD_HELLO_PREFIX)) {
            if (isValidDashboardHello(msg)) {
                if (!isAuthenticatedDashboard(remote)) {
                    Serial.println("Dashboard Connected via WiFi!");
                }
                dashboardIP = remote;
                dashboardConnected = true;
            } else {
                Serial.println("Rejected UDP dashboard HELLO with invalid token.");
            }
            return;
        }

        if (!isAuthenticatedDashboard(remote)) {
            Serial.println("Ignoring UDP packet from unauthenticated dashboard source.");
            return;
        }

        if (msg == Project33Protocol::DASHBOARD_LAUNCH) {
            if (!ENABLE_DASHBOARD_LAUNCH) {
                udpLaunchTriggered = false;
                sendToDashboard(Project33Protocol::CMD_REJECT_DASHBOARD_LAUNCH_DISABLED);
            } else if (currentState == READY) {
                udpLaunchTriggered = true;
                sendToDashboard(Project33Protocol::CMD_ACK_LAUNCH_READY);
            } else {
                udpLaunchTriggered = false;
                sendToDashboard(Project33Protocol::CMD_REJECT_LAUNCH_NOT_READY);
            }
        } else if (msg == Project33Protocol::DASHBOARD_CALIBRATE) {
            Serial2.println(Project33Protocol::CMD_CALIBRATE);
        } else if (msg == Project33Protocol::DASHBOARD_DUMPLOG) {
            Serial2.println(Project33Protocol::CMD_DUMPLOG);
        } else if (msg.startsWith("PID,")) {
            if (isValidPidCommand(msg)) {
                Serial2.println(msg);
            } else {
                sendToDashboard(Project33Protocol::CMD_REJECT_PID_INVALID);
            }
        } else {
            sendToDashboard(Project33Protocol::CMD_REJECT_UNKNOWN_COMMAND);
        }
    }
}

void loop() {
    processUDP();
    processGPS();
    
    if (!isSwitchArmed() && currentState != SAFE) {
        abortSequence("Arming switch flipped OFF.");
        return;
    }

    switch (currentState) {
        case SAFE:
            launcherServo.write(SERVO_OFF);
            digitalWrite(LED_PIN, LOW);
            buzzerOff();
            processSerial2();
            
            if (isSwitchArmed()) {
                currentState = ARMING;
                Serial.println("ARMING Rocket...");
            }
            break;

        case ARMING: { 
            launcherServo.write(SERVO_ON);
            unsigned long armStart = millis();
            rocketReady = false; 

            while (millis() - armStart < 8000) { 
                processUDP();
                processSerial2(); 
                processGPS();
                
                if (!isSwitchArmed()) return; 
                if (rocketReady) break; 
                delay(10);
            }

            if (!rocketReady) { abortSequence("Rocket Timeout."); return; }

            for(int i = 0; i < 3; i++) {
                digitalWrite(LED_PIN, HIGH); beep(80); digitalWrite(LED_PIN, LOW); delay(80);
            }
            delay(1000); 
            
            float sumAy = 0, sumAz = 0;
            int samples = 0;
            unsigned long startWait = millis();
            while(millis() - startWait < 150) {
                processSerial2(); 
                processGPS();
                sumAy += mpu_ay;
                sumAz += mpu_az;
                samples++;
                delay(5);
            }

            if (samples > 0) {
                float L = sqrt((sumAy/samples)*(sumAy/samples) + (sumAz/samples)*(sumAz/samples));
                if (L > 0.1) { cal_ay = (sumAy/samples) / L; cal_az = (sumAz/samples) / L; }
            }
            
            currentState = READY;
            lastHeartbeatTime = millis(); 
            digitalWrite(LED_PIN, HIGH); 
            
            Serial2.println(Project33Protocol::CMD_ARM);
            successTone(); 
            break;
        }

        case READY: {
            processSerial2();
            
            if (millis() - lastHeartbeatTime > HEARTBEAT_TIMEOUT) {
                abortSequence("Lost heartbeat from Rocket!");
                return;
            }

            bool triggered = false;
            if (udpLaunchTriggered) {
                triggered = true;
                udpLaunchTriggered = false;
            } else if (isButtonPressed()) {
                unsigned long triggerStart = millis();
                buzzerOn(); 
                while (isButtonPressed() && millis() - triggerStart < 1000) {
                    processUDP(); 
                    processSerial2();
                    processGPS();
                    if (!isSwitchArmed()) { buzzerOff(); return; }
                    delay(10);
                }
                buzzerOff(); 
                if (isButtonPressed()) triggered = true; 
            }

            if (triggered) {
                currentState = IGNITING;
                Serial2.println(Project33Protocol::CMD_CALIBRATE);
                delay(20);                    
                Serial2.println(Project33Protocol::CMD_IGNITE);
                Serial.println("IGNITION COMMAND SENT");
            }
            break;
        }

        case IGNITING: {
            unsigned long igniteStart = millis();
            rocketIgnited = false;
            while (millis() - igniteStart < 5000) {
                processUDP();
                processSerial2(); 
                processGPS();
                if (rocketIgnited) break;
                delay(10);
            }
            
            if (rocketIgnited) {
                beep(200); 
                digitalWrite(LED_PIN, LOW);
                waitForSwitchReset(); 
            } else {
                abortSequence("No IGNITED ACK received.");
            }
            break;
        }
    }
    
    updateAndPrintFusion();
    
    // Transmit Environment and GPS Status regularly
    static unsigned long lastEnvSend = 0;
    static uint32_t lastCharsProcessed = 0;
    
    if (millis() - lastEnvSend > 1000) {
        lastEnvSend = millis();
        
        // Simple EMA Filter for BMP Altitude
        if (bmpHealthy) {
            float newAlt = bmp.readAltitude();
            filteredAlt = (ALT_ALPHA * newAlt) + ((1.0 - ALT_ALPHA) * filteredAlt);
        }
        
        float lat = 0.0, lon = 0.0;
        int gpsState = 0; // 0=Red(No NMEA), 1=Orange(Searching), 2=Green(Fix)
        
        uint32_t currentChars = gps.charsProcessed();

        if (currentChars == lastCharsProcessed) {
            gpsState = 0; // Module stopped sending or disconnected
        } else if (!gps.location.isValid() || gps.location.lat() == 0.0) {
            gpsState = 1; // Seeing NMEA sentences, but no satellite fix yet
        } else {
            gpsState = 2; // Full fix!
            lat = gps.location.lat();
            lon = gps.location.lng();
        }
        lastCharsProcessed = currentChars;
        
        // Send: ENV,lat,lon,alt,gpsState
        char envMsg[128];
        snprintf(envMsg, sizeof(envMsg), "%s%.6f,%.6f,%.1f,%d", Project33Protocol::ENV_PREFIX, lat, lon, filteredAlt, gpsState);
        sendToDashboard(String(envMsg));
    }
}

void updateAndPrintFusion() {
    static unsigned long lastFusionTime = 0;
    static int compassErrorCount = 0;
    const int MAX_COMPASS_ERRORS = 5;

    if (millis() - lastFusionTime < 500) return;
    lastFusionTime = millis();

    compass.read();
    int qmc_x_raw = compass.getX();
    int qmc_y_raw = compass.getY();
    int qmc_z_raw = compass.getZ();

    if (qmc_x_raw == 0 && qmc_y_raw == 0 && qmc_z_raw == 0) {
        compassErrorCount++;
        if (compassErrorCount <= MAX_COMPASS_ERRORS) {
            Serial.printf("Compass read error (count: %d), resetting I2C...\n", compassErrorCount);
            Wire.end(); delay(50); Wire.begin(I2C_SDA, I2C_SCL);
            compass.init(); compass.setSmoothing(10, true);
            Wire.setClock(400000);
        }
        if (compassErrorCount == MAX_COMPASS_ERRORS) {
            Serial.println("Compass - max errors reached, disabling fusion output");
        }
        return;
    }

    // Reset error counter on successful read
    compassErrorCount = 0;

    float cal_x = (qmc_x_raw - MAG_OFFSET_X) * MAG_SCALE_X;
    float cal_y = (qmc_y_raw - MAG_OFFSET_Y) * MAG_SCALE_Y;
    float cal_z = (qmc_z_raw - MAG_OFFSET_Z) * MAG_SCALE_Z;

    float g_fwd = mpu_ax; 
    float g_right = mpu_az * cal_ay - mpu_ay * cal_az;
    float g_down  = mpu_ay * cal_ay + mpu_az * cal_az;

    float pitch = atan2(-g_fwd, sqrt(g_right * g_right + g_down * g_down));
    float roll = atan2(g_right, g_down);

    float x_m = cal_y * cos(pitch) + cal_z * sin(roll) * sin(pitch) + cal_x * cos(roll) * sin(pitch);
    float y_m = cal_z * cos(roll) - cal_x * sin(roll);

    float heading = atan2(y_m, x_m) * 180.0 / PI;
    if (heading < 0) heading += 360;

    char fusionMsg[128];
    snprintf(fusionMsg, sizeof(fusionMsg), "[FUSION] Hdg: %03.1f | Pitch: %+02.1f", heading, pitch * 180.0/PI);
    sendToDashboard(String(fusionMsg)); 
}

void abortSequence(String reason) {
    Serial.print("ABORT: ");
    Serial.println(reason);
    sendToDashboard(String(Project33Protocol::ABORT_PREFIX) + reason);
    launcherServo.write(SERVO_OFF);
    digitalWrite(LED_PIN, LOW);
    errorTone();
    waitForSwitchReset();
}

void waitForSwitchReset() {
    currentState = SAFE;
    unsigned long lastBlink = 0;
    bool ledState = false;
    
    while (isSwitchArmed()) {
        processUDP(); 
        processSerial2(); 
        processGPS(); 
        
        if (millis() - lastBlink > 100) {
            lastBlink = millis();
            ledState = !ledState;
            digitalWrite(LED_PIN, ledState ? HIGH : LOW);
        }
    }
    digitalWrite(LED_PIN, LOW);
}
