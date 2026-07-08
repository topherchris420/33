/*
 * ROCKET ESP32 CODE (Flight Computer + Stabilization)
 * V4 - Final stable build with Physical Skew Telemetry
 */

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <ESP32Servo.h>
#include <math.h>
#include <stdlib.h>
#include "../../shared/Project33Protocol.h"
#include "deploy_isr.h"

const int RX2_PIN = 16;
const int TX2_PIN = 17;
const int IGNITE_SERVO_PIN = 5;

const int LEFT_SERVO_PIN = 26;
const int RIGHT_SERVO_PIN = 25;
const int UP_SERVO_PIN = 27;
const int DOWN_SERVO_PIN = 14;

const int IGNITE_SERVO_ON = 150;
const int IGNITE_SERVO_OFF = 35;

const int LEFT_CENTER = 115;
const int RIGHT_CENTER = 80;
const int UP_CENTER = 80;
const int DOWN_CENTER = 115;
const int MAX_DEFLECTION = 12;
const float ROLL_COMPLEMENTARY_GYRO_WEIGHT = 0.98;
const float ROLL_COMPLEMENTARY_ACCEL_WEIGHT = 0.02;
const float BOOST_ACCEL_THRESHOLD = 19.62; // ~2g in m/s²; accel-roll unreliable above this

Servo igniteServo;
Servo leftServo, rightServo, upServo, downServo;
Adafruit_MPU6050 mpu;
bool mpuHealthy = false;

String sysState = "IDLE";
float Kp = 0.5;
float Kd = 0.2;
String cmdBuffer = "";
const size_t MAX_SERIAL_COMMAND_LENGTH = 64;

float roll = 0;
float gyroX_offset = 0;
float physical_skew_angle = 0.0;

unsigned long last_time;
unsigned long lastTelemetrySent = 0;
unsigned long lastReadySent = 0;
unsigned long igniteStartTime = 0;

const int FLIGHT_LOG_CAPACITY = 240;
const int LOG_STATE_LEN = 12;

struct FlightLogSample {
    unsigned long timeMs;
    float rollDeg;
    float rateDegS;
    int servoOffset;
    float kp;
    float kd;
    float skewDeg;
    char state[LOG_STATE_LEN];
};

FlightLogSample flightLog[FLIGHT_LOG_CAPACITY];
int flightLogHead = 0;
int flightLogCount = 0;

void recordFlightSample(unsigned long timeMs, float rollDeg, float rateDegS, int servoOffset) {
    FlightLogSample &sample = flightLog[flightLogHead];
    sample.timeMs = timeMs;
    sample.rollDeg = rollDeg;
    sample.rateDegS = rateDegS;
    sample.servoOffset = servoOffset;
    sample.kp = Kp;
    sample.kd = Kd;
    sample.skewDeg = physical_skew_angle;
    sysState.toCharArray(sample.state, LOG_STATE_LEN);

    flightLogHead = (flightLogHead + 1) % FLIGHT_LOG_CAPACITY;
    if (flightLogCount < FLIGHT_LOG_CAPACITY) flightLogCount++;
}

String formatFlightLogSample(const FlightLogSample &sample) {
    return String(Project33Protocol::LOG_PREFIX) + "," +
           String(sample.timeMs) + "," +
           String(sample.rollDeg, 2) + "," +
           String(sample.rateDegS, 2) + "," +
           String(sample.servoOffset) + "," +
           String(sample.state) + "," +
           String(sample.kp, 2) + "," +
           String(sample.kd, 2) + "," +
           String(sample.skewDeg, 2);
}

void dumpFlightLog() {
    Serial2.print(Project33Protocol::LOG_START);
    Serial2.print(",");
    Serial2.println(flightLogCount);

    for (int i = 0; i < flightLogCount; i++) {
        int idx = (flightLogHead - flightLogCount + i + FLIGHT_LOG_CAPACITY) % FLIGHT_LOG_CAPACITY;
        Serial2.println(formatFlightLogSample(flightLog[idx]));
    }

    Serial2.println(Project33Protocol::LOG_END);
}

void centerControlSurfaces() {
    leftServo.write(LEFT_CENTER);
    rightServo.write(RIGHT_CENTER);
    upServo.write(UP_CENTER);
    downServo.write(DOWN_CENTER);
}

bool calibrateGyro() {
    if (!mpuHealthy) {
        gyroX_offset = 0.0;
        physical_skew_angle = 0.0;
        roll = 0.0;
        last_time = millis();
        Serial.println("CALIBRATE skipped: MPU6050 unavailable");
        return false;
    }

    float sumGyroX = 0, sumAccY = 0, sumAccZ = 0;
    int samples = 200;
    for (int i = 0; i < samples; i++) {
        sensors_event_t a, g, temp;
        mpu.getEvent(&a, &g, &temp);
        sumGyroX += g.gyro.x;
        sumAccY += a.acceleration.y;
        sumAccZ += a.acceleration.z;
        delay(5);
    }
    gyroX_offset = sumGyroX / samples;
    float avgY = sumAccY / samples;
    float avgZ = sumAccZ / samples;
    physical_skew_angle = atan2(avgY, avgZ) * 180.0 / PI;
    roll = 0.0;
    last_time = millis();
    return true;
}

bool parseBoundedFloat(const String &text, float &value) {
    if (text.length() == 0 || text.length() >= 24) return false;

    char buffer[24];
    text.toCharArray(buffer, sizeof(buffer));
    char *end = nullptr;
    value = strtof(buffer, &end);

    return end != buffer && *end == '\0' && isfinite(value) && value >= 0.0 && value <= 10.0;
}

bool isValidPidCommand(const String &command, float &newKp, float &newKd) {
    int c1 = command.indexOf(',');
    int c2 = command.indexOf(',', c1 + 1);
    if (c1 <= 0 || c2 <= c1 + 1 || command.indexOf(',', c2 + 1) != -1) return false;

    return parseBoundedFloat(command.substring(c1 + 1, c2), newKp) &&
           parseBoundedFloat(command.substring(c2 + 1), newKd);
}

void processSerialCommands() {
    while (Serial2.available()) {
        char c = Serial2.read();
        if (c == '\n') {
            cmdBuffer.trim();
            if (cmdBuffer == Project33Protocol::CMD_ARM && sysState == "IDLE" && mpuHealthy) {
                sysState = "ARMED";
                calibrateGyro();
            }
#ifdef BENCH_MODE
            else if (cmdBuffer == "IGNITE_FORCE" && sysState == "ARMED" && mpuHealthy) {
                sysState = "IGNITING";
                igniteStartTime = millis();
                igniteServo.write(IGNITE_SERVO_ON);
            }
#endif
            else if (cmdBuffer == Project33Protocol::CMD_IGNITE && sysState == "ARMED" && mpuHealthy) {
                if (!is_fins_deployed()) {
                    Serial.println("CMD_REJECT: Fins not deployed");
                } else {
                    sysState = "IGNITING";
                    igniteStartTime = millis();
                    igniteServo.write(IGNITE_SERVO_ON);
                }
            }
            else if (cmdBuffer == Project33Protocol::CMD_CALIBRATE) {
                calibrateGyro();
            }
            else if (cmdBuffer == Project33Protocol::CMD_DUMPLOG) {
                dumpFlightLog();
            }
            else if (cmdBuffer.startsWith("PID,")) {
                float newKp = 0.0;
                float newKd = 0.0;
                if (isValidPidCommand(cmdBuffer, newKp, newKd)) {
                    Kp = newKp;
                    Kd = newKd;
                    Serial.printf("PID updated: Kp=%.2f, Kd=%.2f\n", Kp, Kd);
                } else {
                    Serial.printf("PID validation failed: %s\n", cmdBuffer.c_str());
                    Serial2.println(Project33Protocol::CMD_REJECT_PID_INVALID);
                }
            }
            cmdBuffer = "";
        } else if (c != '\r') {
            if (cmdBuffer.length() >= MAX_SERIAL_COMMAND_LENGTH) {
                Serial.println("WARNING: Serial command buffer exceeded; dropping partial command.");
                cmdBuffer = "";
                continue;
            }
            cmdBuffer += c;
        }
    }
}

void setup() {
    Serial.begin(115200);
    Serial2.begin(115200, SERIAL_8N1, RX2_PIN, TX2_PIN);
    init_project_33_deploy_system();
    Serial2.setTimeout(20);
    delay(1500);
    Wire.begin(21, 22);
    if (mpu.begin()) {
        mpuHealthy = true;
        Serial.println("MPU6050 initialized successfully");
        mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
        mpu.setGyroRange(MPU6050_RANGE_500_DEG);
        mpu.setFilterBandwidth(MPU6050_BAND_10_HZ);
    } else {
        mpuHealthy = false;
        Serial.println("ERROR: MPU6050 not found - staying IDLE and suppressing READY.");
    }
    ESP32PWM::allocateTimer(0);
    ESP32PWM::allocateTimer(1);
    igniteServo.setPeriodHertz(50);
    igniteServo.attach(IGNITE_SERVO_PIN);
    igniteServo.write(IGNITE_SERVO_OFF);
    leftServo.setPeriodHertz(50);   leftServo.attach(LEFT_SERVO_PIN, 500, 2400);
    rightServo.setPeriodHertz(50);  rightServo.attach(RIGHT_SERVO_PIN, 500, 2400);
    upServo.setPeriodHertz(50);     upServo.attach(UP_SERVO_PIN, 500, 2400);
    downServo.setPeriodHertz(50);   downServo.attach(DOWN_SERVO_PIN, 500, 2400);
    centerControlSurfaces();
    calibrateGyro();
}

void loop() {
    unsigned long current_time = millis();
    processSerialCommands();

    if (!mpuHealthy) {
        centerControlSurfaces();
        igniteServo.write(IGNITE_SERVO_OFF);
        delay(20);
        return;
    }

    float dt = (current_time - last_time) / 1000.0;
    if (dt <= 0) dt = 0.001;
    last_time = current_time;

    sensors_event_t a, g, temp;
    mpu.getEvent(&a, &g, &temp);

    // C2: Hardware-timed zero-blocking deployment
    if (a.acceleration.x > DEPLOY_ACCEL_THRESHOLD_G) {
        trigger_deployment_sequence(50000); // 50ms delay
    }

    float raw_rate_rad = g.gyro.x - gyroX_offset;
    float rate_deg_s = raw_rate_rad * 180.0 / PI;
    float accel_roll_deg = atan2(a.acceleration.y, a.acceleration.z) * 180.0 / PI - physical_skew_angle;
    float gyro_roll_deg = roll + (rate_deg_s * dt);

    // Boost detection: when total accel magnitude exceeds ~2g, the
    // accelerometer reads thrust+gravity, making accel_roll_deg unreliable.
    // Fall back to pure gyro integration during powered flight.
    float accel_mag = sqrt(a.acceleration.x * a.acceleration.x +
                           a.acceleration.y * a.acceleration.y +
                           a.acceleration.z * a.acceleration.z);
    bool in_boost = (accel_mag > BOOST_ACCEL_THRESHOLD) || (sysState == "FLIGHT");

    if (in_boost) {
        roll = gyro_roll_deg; // pure gyro — no accel correction
    } else {
        roll = (ROLL_COMPLEMENTARY_GYRO_WEIGHT * gyro_roll_deg) + (ROLL_COMPLEMENTARY_ACCEL_WEIGHT * accel_roll_deg);
    }

    float output = (Kp * roll) + (Kd * rate_deg_s);
    int servo_offset = constrain((int)output, -MAX_DEFLECTION, MAX_DEFLECTION);

    if (sysState == "FLIGHT") {
        leftServo.write(LEFT_CENTER + servo_offset);
        rightServo.write(RIGHT_CENTER + servo_offset);
        upServo.write(UP_CENTER + servo_offset);
        downServo.write(DOWN_CENTER + servo_offset);
    } else {
        centerControlSurfaces();
        servo_offset = 0;
    }

    if (sysState == "IGNITING" && (current_time - igniteStartTime > 2500)) {
        igniteServo.write(IGNITE_SERVO_OFF);
        // Bench note: FLIGHT state reflects actuation commanded, not confirmed ignition;
        // do not treat this timer-only transition as live propulsion telemetry.
        sysState = "FLIGHT";
        Serial2.println(Project33Protocol::IGNITED);
    }

    if (current_time - lastTelemetrySent >= 50) {
        // Telemetry payload including Skew Angle
        String payload = String(Project33Protocol::DATA_PREFIX) + String(a.acceleration.x, 2) + "," +
                         String(a.acceleration.y, 2) + "," + String(a.acceleration.z, 2) + "," +
                         String(roll, 2) + "," + String(rate_deg_s, 2) + "," +
                         String(servo_offset) + "," + sysState + "," +
                         String(Kp, 2) + "," + String(Kd, 2) + "," +
                         String(physical_skew_angle, 2);
        Serial2.println(payload);
        recordFlightSample(current_time, roll, rate_deg_s, servo_offset);
        lastTelemetrySent = current_time;
    }

    if (sysState == "IDLE" && mpuHealthy && (current_time - lastReadySent >= 1000)) {
        Serial2.println(Project33Protocol::READY);
        lastReadySent = current_time;
    }
}
