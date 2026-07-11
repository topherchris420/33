#ifndef DEPLOY_ISR_H
#define DEPLOY_ISR_H

#include <stdint.h>
#include <stdbool.h>

// Initialize the hardware-timed deployment system.
// Configures DEPLOY_OUTPUT_PIN as output (safe LOW) and creates the esp_timer.
void init_project_33_deploy_system();

// Arm the deployment timer. Call when IMU detects threshold.
// delay_us: microseconds after call to fire GPIO.
void trigger_deployment_sequence(uint64_t delay_us);

// Check if fins have been deployed.
bool is_fins_deployed();

// Reset deployment state for test harnesses
void reset_fins_deployed();

// Deployment output GPIO. Must not collide with any servo, UART, or I2C pin
// in Firmware/Rocket/src/main.cpp (see docs/WIRING.md).
extern const int DEPLOY_OUTPUT_PIN;

// Egress detection threshold, in g and pre-converted to the m/s² units that
// Adafruit_MPU6050 reports. Compare sensor readings against the _MS2 value.
extern const float DEPLOY_ACCEL_THRESHOLD_G;
extern const float DEPLOY_ACCEL_THRESHOLD_MS2;

#endif // DEPLOY_ISR_H
