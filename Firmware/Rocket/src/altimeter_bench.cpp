// Separate pressure-observation image. No actuator, command or radio interface.
#ifdef PROJECT33_ALTIMETER_BENCH
#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>
#include <Adafruit_BMP085.h>
#include <esp_system.h>
#include <esp_ota_ops.h>
#include <math.h>

static Adafruit_BMP085 barometer;
static bool initialized = false;
static char bootId[17], elf[65];
static uint32_t sequence = 0, lastSample = 0, lastInit = 0;

void setup() {
    Serial.begin(115200);
    Wire.begin(21, 22);
    Wire.setTimeOut(20);
    snprintf(bootId, sizeof(bootId), "%08lx%08lx", (unsigned long)esp_random(), (unsigned long)esp_random());
    const esp_app_desc_t *description = esp_ota_get_app_description();
    for (size_t i = 0; i < 32; ++i) snprintf(elf + i * 2, 3, "%02x", description->app_elf_sha256[i]);
    initialized = barometer.begin();
}

void loop() {
    const uint32_t now = millis();
    if (!initialized && uint32_t(now - lastInit) >= 5000) {
        lastInit = now;
        initialized = barometer.begin();
    }
    if (uint32_t(now - lastSample) < 200) return;
    lastSample = now;
    bool valid = false;
    if (initialized) {
        Wire.beginTransmission(0x77);
        Wire.write(0xd0);
        valid = Wire.endTransmission(false) == 0 && Wire.requestFrom(uint8_t(0x77), uint8_t(1)) == 1 && Wire.read() == 0x55;
    }
    float pressure = valid ? barometer.readPressure() : NAN;
    valid = valid && isfinite(pressure) && pressure > 0 && pressure <= 120000;
    Serial.printf("P33BARO,1,%s,%lu,%lu,%u,", bootId, (unsigned long)sequence++, (unsigned long)now, unsigned(valid));
    if (valid) Serial.printf("%.1f,", pressure);
    else Serial.print("nan,");
    Serial.println(elf);
}
#endif
