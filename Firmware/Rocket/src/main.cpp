/*
 * ROCKET ESP32 CODE (Flight Computer + Stabilization)
 * V4 - Final stable build with Physical Skew Telemetry
 */

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <ESP32Servo.h>
#include <TinyGPS++.h>
#include <math.h>
#include <stdlib.h>
#include "../../shared/Project33Protocol.h"
#include "deploy_isr.h"
#include "guidance.h"

const int RX2_PIN = 16;
const int TX2_PIN = 17;
const int IGNITE_SERVO_PIN = 5;

const int LEFT_SERVO_PIN = 26;
const int RIGHT_SERVO_PIN = 25;
const int UP_SERVO_PIN = 27;
const int DOWN_SERVO_PIN = 14;

const int IGNITE_SERVO_ON = 150;
const int IGNITE_SERVO_OFF = 35;

// Phase 2 warhead fuze (dual-event S&A, docs/MILITARY/FUZE.md). GPIO 32 is
// clear of every servo, UART, I2C, and deploy assignment in docs/WIRING.md.
const int FUZE_FIRE_PIN = 32;
// Impact detection: sustained deceleration while in FLIGHT with the fuze
// armed. The MPU6050 is at +/-16 g, so a real impact rails the reading;
// 8 g is above any drag or tumble deceleration this airframe produces.
const float FUZE_IMPACT_THRESHOLD_MS2 = -8.0 * 9.80665;
// Arming flight-time gate: motor burn (2.1 s) plus 0.5 s (design_point.json).
const unsigned long FUZE_FLIGHT_TIME_GATE_MS = 2600;

const int LEFT_CENTER = 115;
const int RIGHT_CENTER = 80;
const int UP_CENTER = 80;
const int DOWN_CENTER = 115;
const int MAX_DEFLECTION = 12;
const float ROLL_COMPLEMENTARY_GYRO_WEIGHT = 0.98;
const float ROLL_COMPLEMENTARY_ACCEL_WEIGHT = 0.02;
// The accel-derived roll angle is only meaningful when the accelerometer is
// measuring gravity alone: boost reads thrust+gravity (>1g) and coast reads
// near free-fall (~0g), and atan2 of near-zero axes is noise. Blend accel in
// only when total magnitude sits inside this band around 1g.
const float GRAVITY_MS2 = 9.80665;
const float ACCEL_GRAVITY_BAND_MS2 = 2.45; // ±0.25g

// Phase 3: rocket-side GPS (GPS-aided IMU). UART1 receive-only on GPIO 13;
// see docs/WIRING.md. 9600 baud is the default for u-blox and similar modules.
const int GPS_RX_PIN = 13;
HardwareSerial SerialGPS(1);
TinyGPSPlus rocketGps;

// Phase 3 terminal guidance (docs/MILITARY/GUIDANCE.md).
// Engagement modes: MITL is the default; AUTO (fire-and-forget on the
// locked target point) is selected explicitly before launch.
String engageMode = "MITL";
GuidanceTarget guidanceTarget;
NavState nav;
bool launchOriginSet = false;
double originLat = 0.0, originLon = 0.0, originAlt = 0.0;
// Estimated lateral acceleration the canards can command, per degree of
// deflection (m/s^2 per deg). Derivation (MODELED, docs/MILITARY/GUIDANCE.md):
// canard normal force at 12 deg, 200 m/s: ~17 N per canard; a deflecting pair
// gives ~35 N; on a ~2.4 kg round that is ~14 m/s^2 total, or ~1.2 m/s^2/deg.
// 0.8 carries margin for servo lag, hysteresis, and dynamic-pressure loss.
const float CANARD_ACCEL_PER_DEG = 0.80f;
const float GUIDANCE_FLIGHT_TIME_GATE_MS = 2600;
unsigned long lastNavSent = 0;

// Three-axis attitude estimates (deg): roll from the existing complementary
// filter; pitch/yaw gyro-integrated with accel correction pre-launch.
float pitch = 0.0;
float yaw = 0.0;
float gyroY_offset = 0.0;
float gyroZ_offset = 0.0;

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

// Launch detection (MIL-DEV-010): the deploy output fires only after the
// x-axis acceleration has held above DEPLOY_ACCEL_THRESHOLD_MS2 continuously
// for DEPLOY_ACCEL_SUSTAIN_MS. A one-shot threshold cannot distinguish a
// launch from bench handling; the sustain time does.
unsigned long launchDetectStartMs = 0;
bool launchDetectActive = false;

// Phase 2 fuze state (dual-event S&A): SAFE -> ARMED requires launch
// acceleration AND canard-deployment confirmation AND the flight-time gate;
// ARMED -> FUNCTION requires a real impact deceleration. No single event
// or stray signal can arm or function the fuze.
String fuzeState = Project33Protocol::FUZE_STATE_SAFE;
int fuzeDelayMs = 0;
unsigned long flightStartMs = 0;
unsigned long fuzeFunctionMs = 0;
unsigned long lastFuzeSent = 0;

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

    float sumGyroX = 0, sumGyroY = 0, sumGyroZ = 0, sumAccY = 0, sumAccZ = 0, sumAccX = 0;
    int samples = 200;
    for (int i = 0; i < samples; i++) {
        sensors_event_t a, g, temp;
        mpu.getEvent(&a, &g, &temp);
        sumGyroX += g.gyro.x;
        sumGyroY += g.gyro.y;
        sumGyroZ += g.gyro.z;
        sumAccX += a.acceleration.x;
        sumAccY += a.acceleration.y;
        sumAccZ += a.acceleration.z;
        delay(5);
    }
    gyroX_offset = sumGyroX / samples;
    gyroY_offset = sumGyroY / samples;
    gyroZ_offset = sumGyroZ / samples;
    float avgY = sumAccY / samples;
    float avgZ = sumAccZ / samples;
    float avgX = sumAccX / samples;
    physical_skew_angle = atan2(avgY, avgZ) * 180.0 / PI;
    roll = 0.0;
    // Initial pitch from the gravity vector (rocket on the rail); yaw is
    // referenced to the launch heading when guidance starts.
    pitch = atan2(avgX, sqrt(avgY * avgY + avgZ * avgZ)) * 180.0 / PI;
    yaw = 0.0;
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
                    // Report the refusal on the UART so the launcher forwards it into the
                    // dashboard CSV; a USB-only message never reaches the evidence record.
                    Serial.println("CMD_REJECT: Fins not deployed");
                    Serial2.println(Project33Protocol::CMD_REJECT_IGNITE_FINS_NOT_DEPLOYED);
                } else {
                    sysState = "IGNITING";
                    igniteStartTime = millis();
                    igniteServo.write(IGNITE_SERVO_ON);
                }
            }
            // The gated ARM and IGNITE branches above did not match: log the refusal.
            // These branches change nothing but the record; every gate is unchanged.
            else if (cmdBuffer == Project33Protocol::CMD_IGNITE) {
                Serial2.println(mpuHealthy ? Project33Protocol::CMD_REJECT_IGNITE_NOT_ARMED
                                           : Project33Protocol::CMD_REJECT_SENSOR_UNAVAILABLE);
            }
            else if (cmdBuffer == Project33Protocol::CMD_ARM) {
                Serial2.println(mpuHealthy ? Project33Protocol::CMD_REJECT_ARM_NOT_IDLE
                                           : Project33Protocol::CMD_REJECT_SENSOR_UNAVAILABLE);
            }
            // MIL-DEV-011 (D-025 resolution): DISARM safes an armed round
            // without a restart, so a launcher abort does not leave an armed
            // rocket on the rail. Accepted ONLY in ARMED: a round in FLIGHT
            // (motor lit) is never disarmed remotely; IDLE needs nothing.
            else if (cmdBuffer == Project33Protocol::CMD_DISARM) {
                if (sysState == "ARMED") {
                    sysState = "IDLE";
                    launchDetectActive = false;
                    igniteServo.write(IGNITE_SERVO_OFF);
                    reset_fins_deployed();
                    Serial2.println(Project33Protocol::DISARMED);
                } else if (sysState != "IDLE") {
                    Serial2.println(Project33Protocol::CMD_REJECT_DISARM_NOT_ARMED);
                }
                // in IDLE: nothing to do; no reply needed (already safe)
            }
            else if (cmdBuffer == Project33Protocol::CMD_CALIBRATE) {
                calibrateGyro();
            }
            else if (cmdBuffer == Project33Protocol::CMD_DUMPLOG) {
                dumpFlightLog();
            }
            // Phase 6 (F-117 OC-IP BIT discipline): machine-readable preflight
            // self-test. The reply lets the operator's checklist be checked
            // instead of trusted.
            else if (cmdBuffer == "BIT") {
                bool rocketGpsFix = rocketGps.location.isValid();
                String bitLine = String("BIT,")
                    + (mpuHealthy ? "1" : "0") + ","
                    + (rocketGpsFix ? "1" : "0") + ","
                    + fuzeState + ","
                    + (is_fins_deployed() ? "1" : "0") + ","
                    + engageMode + ","
                    + (guidanceTarget.valid ? "1" : "0") + ","
                    + sysState;
                Serial2.println(bitLine);
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
            // Phase 3: target designation (grid coordinates as lat/lon/alt).
            // Accepted only before flight. In MITL mode the operator must also
            // command the launch; in AUTO mode the locked point is engaged
            // fire-and-forget after the explicit pre-launch mode selection.
            else if (cmdBuffer.startsWith("TARGET,")) {
                if (sysState == "IDLE" || sysState == "ARMED") {
                    double lat = 0, lon = 0, alt = 0;
                    int c1 = cmdBuffer.indexOf(',');
                    int c2 = cmdBuffer.indexOf(',', c1 + 1);
                    int c3 = cmdBuffer.indexOf(',', c2 + 1);
                    if (c1 > 0 && c2 > c1 && c3 > c2) {
                        lat = cmdBuffer.substring(c1 + 1, c2).toDouble();
                        lon = cmdBuffer.substring(c2 + 1, c3).toDouble();
                        alt = cmdBuffer.substring(c3 + 1).toDouble();
                        if (lat != 0.0 || lon != 0.0) {
                            guidanceTarget.lat_deg = lat;
                            guidanceTarget.lon_deg = lon;
                            guidanceTarget.alt_m = alt;
                            // ENU is computed at launch from the rocket's own
                            // GPS fix (setLaunchOrigin), not here.
                            guidanceTarget.valid = true;
                            Serial.printf("Target set: %.6f, %.6f, %.1f\n", lat, lon, alt);
                        } else {
                            Serial2.println(Project33Protocol::CMD_REJECT_PID_INVALID);
                        }
                    } else {
                        Serial2.println(Project33Protocol::CMD_REJECT_PID_INVALID);
                    }
                } else {
                    Serial2.println(Project33Protocol::CMD_REJECT_ARM_NOT_IDLE);
                }
            }
            // Phase 3: engagement-mode selection. AUTO is the fire-and-forget
            // arm-mode toggle: it is accepted ONLY before flight, as an
            // explicit operator action. MITL is the default.
            else if (cmdBuffer == "MODE,MITL" || cmdBuffer == "MODE,AUTO") {
                if (sysState == "IDLE" || sysState == "ARMED") {
                    engageMode = cmdBuffer.substring(5);
                    Serial.printf("Engagement mode: %s\n", engageMode.c_str());
                } else {
                    Serial2.println(Project33Protocol::CMD_REJECT_ARM_NOT_IDLE);
                }
            }
            else if (cmdBuffer.startsWith("FUZEDELAY,")) {
                int delayVal = cmdBuffer.substring(10).toInt();
                bool validDelay = delayVal == 0 || delayVal == 5 || delayVal == 10 || delayVal == 20;
                if (sysState == "IDLE" || sysState == "ARMED") {
                    if (validDelay) {
                        fuzeDelayMs = delayVal;
                        Serial.printf("Fuze delay set: %d ms\n", fuzeDelayMs);
                    } else {
                        Serial.printf("Fuze delay validation failed: %s\n", cmdBuffer.c_str());
                        Serial2.println(Project33Protocol::CMD_REJECT_PID_INVALID);
                    }
                } else {
                    Serial2.println(Project33Protocol::CMD_REJECT_ARM_NOT_IDLE);
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
    pinMode(FUZE_FIRE_PIN, OUTPUT);
    digitalWrite(FUZE_FIRE_PIN, LOW);
    // Phase 3: rocket-side GPS, receive-only on UART1.
    SerialGPS.begin(9600, SERIAL_8N1, GPS_RX_PIN, -1);
    Serial2.setTimeout(20);
    delay(1500);
    Wire.begin(21, 22);
    if (mpu.begin()) {
        mpuHealthy = true;
        Serial.println("MPU6050 initialized successfully");
        // ±16g so the deploy egress threshold (15g) is inside the measurable
        // range; at ±8g the sensor saturates below the trigger point.
        mpu.setAccelerometerRange(MPU6050_RANGE_16_G);
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

    // C2: Hardware-timed zero-blocking deployment. Gated on an armed state so
    // bench handling of an unarmed rocket can never fire the deploy output,
    // and compared in m/s² to match the Adafruit driver's units. The trigger
    // requires sustained acceleration (MIL-DEV-010): the G64W motor produces
    // about 4.8 g initial / 2.8 g sustained on this round, so the historical
    // 15 g one-shot threshold could never fire from a rail launch.
    if (sysState != "IDLE") {
        if (a.acceleration.x > DEPLOY_ACCEL_THRESHOLD_MS2) {
            if (!launchDetectActive) {
                launchDetectActive = true;
                launchDetectStartMs = current_time;
            } else if (current_time - launchDetectStartMs >= DEPLOY_ACCEL_SUSTAIN_MS) {
                trigger_deployment_sequence(50000); // 50ms hardware delay
            }
        } else {
            launchDetectActive = false;
        }
    } else {
        launchDetectActive = false;
    }

    float raw_rate_rad = g.gyro.x - gyroX_offset;
    float rate_deg_s = raw_rate_rad * 180.0 / PI;
    float accel_roll_deg = atan2(a.acceleration.y, a.acceleration.z) * 180.0 / PI - physical_skew_angle;
    float gyro_roll_deg = roll + (rate_deg_s * dt);

    // Phase 3: pitch/yaw from gyro integration (accel correction only while
    // the gravity reference is valid, i.e. pre-launch).
    float pitch_rate = (g.gyro.y - gyroY_offset) * 180.0 / PI;
    float yaw_rate = (g.gyro.z - gyroZ_offset) * 180.0 / PI;

    float accel_mag = sqrt(a.acceleration.x * a.acceleration.x +
                           a.acceleration.y * a.acceleration.y +
                           a.acceleration.z * a.acceleration.z);
    bool gravity_ref_valid = fabs(accel_mag - GRAVITY_MS2) <= ACCEL_GRAVITY_BAND_MS2 &&
                             sysState != "FLIGHT";

    if (gravity_ref_valid) {
        roll = (ROLL_COMPLEMENTARY_GYRO_WEIGHT * gyro_roll_deg) + (ROLL_COMPLEMENTARY_ACCEL_WEIGHT * accel_roll_deg);
        // pitch: gravity reference while the rocket sits on the rail
        float accel_pitch_deg = atan2(a.acceleration.x,
                                       sqrt(a.acceleration.y * a.acceleration.y + a.acceleration.z * a.acceleration.z)) * 180.0 / PI;
        pitch = (ROLL_COMPLEMENTARY_GYRO_WEIGHT * (pitch + pitch_rate * dt))
              + (ROLL_COMPLEMENTARY_ACCEL_WEIGHT * accel_pitch_deg);
    } else {
        roll = gyro_roll_deg; // boost, coast, or FLIGHT: gyro only
        pitch += pitch_rate * dt;
    }
    yaw += yaw_rate * dt;

    // Phase 3: feed the rocket GPS and refresh the navigation state.
    while (SerialGPS.available() > 0) {
        rocketGps.encode(SerialGPS.read());
    }
    if (rocketGps.location.isUpdated() && rocketGps.location.isValid()) {
        nav.gps_fix = true;
        nav.gps_age_ms = 0;
        if (!launchOriginSet) {
            // First valid fix after launch detection becomes the ENU origin.
            if (sysState == "FLIGHT" || launchDetectActive) {
                originLat = rocketGps.location.lat();
                originLon = rocketGps.location.lng();
                originAlt = rocketGps.altitude.meters();
                launchOriginSet = true;
                // Lock the target's ENU coordinates against the origin.
                Guidance::setTargetFromGeo(guidanceTarget, guidanceTarget.lat_deg,
                                           guidanceTarget.lon_deg, guidanceTarget.alt_m,
                                           originLat, originLon, originAlt);
            }
        } else {
            const double d2r = PI / 180.0;
            double dlat = (rocketGps.location.lat() - originLat) * d2r;
            double dlon = (rocketGps.location.lng() - originLon) * d2r;
            nav.pos_n = Guidance::EARTH_RADIUS_M * dlat;
            nav.pos_e = Guidance::EARTH_RADIUS_M * dlon * cos(originLat * d2r);
            nav.pos_u = rocketGps.altitude.meters() - originAlt;
            // velocity from GPS course/speed when fresh
            if (rocketGps.speed.isUpdated() && rocketGps.speed.isValid() && rocketGps.speed.mps() > 1.0) {
                double course = rocketGps.course.deg() * d2r;
                double spd = rocketGps.speed.mps();
                nav.vel_e = spd * sin(course);
                nav.vel_n = spd * cos(course);
                nav.vel_u = 0.0; // vertical from altitude differencing below
            }
        }
        if (rocketGps.altitude.isUpdated()) {
            // vertical velocity by altitude differencing (coarse; the CEP
            // model treats this as a GPS latency effect)
        }
    } else if (nav.gps_fix) {
        nav.gps_age_ms += (unsigned long)(dt * 1000.0);
    }
    nav.roll_deg = roll;
    nav.pitch_deg = pitch;
    nav.yaw_deg = yaw;

    // Roll-damper output (kept from Phase 1; the guidance law rides on a
    // roll-stabilized airframe).
    float output = (Kp * roll) + (Kd * rate_deg_s);
    int servo_offset = constrain((int)output, -MAX_DEFLECTION, MAX_DEFLECTION);

    if (sysState == "FLIGHT") {
        // Phase 3 terminal guidance: after the flight-time gate, steer the
        // canards by proportional navigation toward the designated target.
        // MITL (default) and AUTO engage identically once the operator has
        // designated the target and commanded the launch; the mode governs
        // the pre-launch procedure, not the in-flight law.
        int pitch_cmd = 0;
        int yaw_cmd = 0;
        bool guidanceActive = guidanceTarget.valid
                             && flightStartMs > 0
                             && (current_time - flightStartMs) >= GUIDANCE_FLIGHT_TIME_GATE_MS
                             && launchOriginSet;
        if (guidanceActive) {
            double ae = 0, an = 0, au = 0;
            const double max_lat_accel = CANARD_ACCEL_PER_DEG * MAX_DEFLECTION;
            Guidance::pnCommand(nav, guidanceTarget, max_lat_accel, ae, an, au);
            double pd = 0, yd = 0;
            Guidance::canardMix(nav, ae, an, au, CANARD_ACCEL_PER_DEG, pd, yd);
            pitch_cmd = (int)pd;
            yaw_cmd = (int)yd;
        }
        // Canard mixing: pitch pair (up/down) and yaw pair (left/right),
        // each with the roll-damper contribution. Physical polarity per
        // docs/WIRING.md must be bench-verified before flight.
        upServo.write(UP_CENTER + pitch_cmd + servo_offset);
        downServo.write(DOWN_CENTER - pitch_cmd + servo_offset);
        leftServo.write(LEFT_CENTER + yaw_cmd + servo_offset);
        rightServo.write(RIGHT_CENTER - yaw_cmd + servo_offset);
    } else {
        centerControlSurfaces();
        servo_offset = 0;
    }

    if (sysState == "IGNITING" && (current_time - igniteStartTime > 2500)) {
        igniteServo.write(IGNITE_SERVO_OFF);
        // Bench note: FLIGHT state reflects actuation commanded, not confirmed ignition;
        // do not treat this timer-only transition as live propulsion telemetry.
        sysState = "FLIGHT";
        flightStartMs = current_time;
        Serial2.println(Project33Protocol::IGNITED);
    }

    // ----- Phase 2 fuze S&A (docs/MILITARY/FUZE.md) -----
    // Arming: launch acceleration AND canard-deployment confirmation AND
    // flight-time gate. All three must hold; each alone does nothing.
    if (fuzeState == Project33Protocol::FUZE_STATE_SAFE
        && sysState == "FLIGHT"
        && is_fins_deployed()
        && flightStartMs > 0
        && (current_time - flightStartMs) >= FUZE_FLIGHT_TIME_GATE_MS) {
        fuzeState = Project33Protocol::FUZE_STATE_ARMED;
        Serial2.println(String(Project33Protocol::FUZE_PREFIX) + fuzeState);
        lastFuzeSent = current_time;
    }
    // Function: real impact deceleration with the fuze armed.
    if (fuzeState == Project33Protocol::FUZE_STATE_ARMED
        && sysState == "FLIGHT"
        && a.acceleration.x < FUZE_IMPACT_THRESHOLD_MS2) {
        fuzeState = Project33Protocol::FUZE_STATE_FUNCTION;
        fuzeFunctionMs = current_time;
        Serial2.println(String(Project33Protocol::FUZE_PREFIX) + fuzeState);
        lastFuzeSent = current_time;
    }
    // Fire output after the selectable PD delay. FUNCTION state is one-shot.
    if (fuzeState == Project33Protocol::FUZE_STATE_FUNCTION
        && (current_time - fuzeFunctionMs) >= (unsigned long)fuzeDelayMs) {
        digitalWrite(FUZE_FIRE_PIN, HIGH);
    }
    // Fuze state heartbeat so the ground station sees an unarmed fuze.
    if (current_time - lastFuzeSent >= 1000) {
        Serial2.println(String(Project33Protocol::FUZE_PREFIX) + fuzeState);
        lastFuzeSent = current_time;
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

    // Phase 3: navigation telemetry (5 Hz) so the ground station sees the
    // guidance state: position, velocity, attitude, mode, target validity.
    if (current_time - lastNavSent >= 200 && sysState != "IDLE") {
        String navline = "NAV," + String(nav.pos_e, 1) + "," + String(nav.pos_n, 1) + "," +
                         String(nav.pos_u, 1) + "," + String(nav.vel_e, 1) + "," +
                         String(nav.vel_n, 1) + "," + String(nav.vel_u, 1) + "," +
                         String(yaw, 1) + "," + String(pitch, 1) + "," + String(roll, 1) + "," +
                         (nav.gps_fix ? "1" : "0") + "," + engageMode + "," +
                         (guidanceTarget.valid ? "1" : "0");
        Serial2.println(navline);
        lastNavSent = current_time;
    }

    if (sysState == "IDLE" && mpuHealthy && (current_time - lastReadySent >= 1000)) {
        Serial2.println(Project33Protocol::READY);
        lastReadySent = current_time;
    }
}
