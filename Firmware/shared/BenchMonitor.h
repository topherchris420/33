// Standalone stationary bench instrumentation. Included only by monitor builds.
#pragma once
#include <Arduino.h>
#include <Wire.h>
#include <SPI.h> // Adafruit BusIO compiles its SPI adapter even for I2C-only sensors.
#include <esp_system.h>
#include <esp_ota_ops.h>
#include <math.h>

#ifdef PROJECT33_MONITOR_ROCKET
#include <Adafruit_MPU6050.h>
static Adafruit_MPU6050 monitorImu;
static const char *monitorRole = "rocket";
static bool monitorSensorInitialized = false;
#else
#include <Adafruit_BMP085.h>
#include <QMC5883LCompass.h>
#include <TinyGPS++.h>
static Adafruit_BMP085 monitorBarometer;
static QMC5883LCompass monitorCompass;
static TinyGPSPlus monitorGps;
static HardwareSerial monitorGpsSerial(1);
static const char *monitorRole = "launcher";
static bool monitorSensorInitialized = false;
#endif

static char monitorBoot[17];
static char monitorElf[65];
static uint32_t monitorSequence = 0;
static uint32_t monitorLastSample = 0;
static uint32_t monitorLastIdentity = 0;
static uint32_t monitorLastInitAttempt = 0;

static bool monitorRegister(uint8_t address, uint8_t reg, uint8_t expected) {
    Wire.beginTransmission(address);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0) return false;
    if (Wire.requestFrom(address, uint8_t(1)) != 1) return false;
    return Wire.read() == expected;
}

static void monitorPrefix(const char *kind, uint32_t now) {
    Serial.printf("%s,1,%s,%s,%lu,%lu,", kind, monitorRole, monitorBoot,
                  (unsigned long)monitorSequence++, (unsigned long)now);
}

static void monitorIdentity(uint32_t now) {
    monitorPrefix("P33ID", now);
    Serial.println(monitorElf);
}

static void monitorInitializeSensor() {
#ifdef PROJECT33_MONITOR_ROCKET
    monitorSensorInitialized = monitorImu.begin();
#else
    monitorSensorInitialized = monitorBarometer.begin();
#endif
}

void setup() {
    Serial.begin(115200);
    Wire.begin(21, 22);
    Wire.setTimeOut(20);
    snprintf(monitorBoot, sizeof(monitorBoot), "%08lx%08lx",
             (unsigned long)esp_random(), (unsigned long)esp_random());
    const esp_app_desc_t *description = esp_ota_get_app_description();
    for (size_t i = 0; i < 32; ++i) {
        snprintf(monitorElf + i * 2, 3, "%02x", description->app_elf_sha256[i]);
    }
    monitorInitializeSensor();
#ifndef PROJECT33_MONITOR_ROCKET
    monitorCompass.init();
    monitorGpsSerial.begin(9600, SERIAL_8N1, 4, -1);
#endif
    monitorIdentity(millis());
}

void loop() {
#ifndef PROJECT33_MONITOR_ROCKET
    // Bounded work per iteration, including a noisy or continuously active input.
    for (int i = 0; i < 128 && monitorGpsSerial.available(); ++i) {
        monitorGps.encode(monitorGpsSerial.read());
    }
#endif
    const uint32_t now = millis();
    if (!monitorSensorInitialized && uint32_t(now - monitorLastInitAttempt) >= 5000) {
        monitorLastInitAttempt = now;
        monitorInitializeSensor();
    }
    if (uint32_t(now - monitorLastSample) < 500) return;
    monitorLastSample = now;
    if (uint32_t(now - monitorLastIdentity) >= 5000) {
        monitorLastIdentity = now;
        monitorIdentity(now);
    }
    monitorPrefix("P33SYS", now);
    Serial.printf("%u,%lu,%lu\n", unsigned(esp_reset_reason()),
                  (unsigned long)ESP.getFreeHeap(), (unsigned long)ESP.getMinFreeHeap());

#ifdef PROJECT33_MONITOR_ROCKET
    sensors_event_t acceleration, gyro, temperature;
    bool valid = monitorSensorInitialized && monitorRegister(0x68, 0x75, 0x68);
    if (valid) {
        valid = monitorImu.getEvent(&acceleration, &gyro, &temperature) &&
                isfinite(acceleration.acceleration.x) && isfinite(acceleration.acceleration.y) &&
                isfinite(acceleration.acceleration.z) && isfinite(gyro.gyro.x) &&
                isfinite(gyro.gyro.y) && isfinite(gyro.gyro.z) && isfinite(temperature.temperature);
    }
    monitorPrefix("P33S", now);
    Serial.printf("mpu6050,%u,", unsigned(valid));
    if (valid) {
        Serial.printf("%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.3f\n",
            acceleration.acceleration.x, acceleration.acceleration.y, acceleration.acceleration.z,
            gyro.gyro.x, gyro.gyro.y, gyro.gyro.z, temperature.temperature);
    } else {
        Serial.println("nan,nan,nan,nan,nan,nan,nan");
    }
#else
    bool valid = monitorSensorInitialized && monitorRegister(0x77, 0xd0, 0x55);
    float temperature = NAN, pressure = NAN;
    if (valid) {
        temperature = monitorBarometer.readTemperature();
        pressure = monitorBarometer.readPressure();
        valid = isfinite(temperature) && isfinite(pressure) && pressure > 0;
    }
    monitorPrefix("P33S", now);
    Serial.printf("bmp180,%u,", unsigned(valid));
    if (valid) Serial.printf("%.3f,%.1f\n", temperature, pressure);
    else Serial.println("nan,nan");

    Wire.beginTransmission(0x0d);
    const bool compassResponded = Wire.endTransmission() == 0;
    monitorPrefix("P33S", now);
    if (compassResponded) {
        monitorCompass.read();
        Serial.printf("qmc5883l,1,%d,%d,%d\n", monitorCompass.getX(), monitorCompass.getY(), monitorCompass.getZ());
    } else Serial.println("qmc5883l,0,nan,nan,nan");

    const bool gpsValid = monitorGps.location.isValid() && monitorGps.location.age() <= 2000;
    monitorPrefix("P33S", now);
    if (gpsValid) Serial.printf("gps,1,%.7f,%.7f\n", monitorGps.location.lat(), monitorGps.location.lng());
    else Serial.println("gps,0,nan,nan");
#endif
}
