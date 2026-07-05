#ifndef DEPLOY_ISR_H
#define DEPLOY_ISR_H

#include <stdint.h>
#include <stdbool.h>

// Initialize the hardware-timed deployment system.
// Configures GPIO_NUM_5 as output (safe LOW) and creates the esp_timer.
void init_project_33_deploy_system();

// Arm the deployment timer. Call when IMU detects threshold.
// delay_us: microseconds after call to fire GPIO.
void trigger_deployment_sequence(uint64_t delay_us);

// Check if fins have been deployed.
bool is_fins_deployed();

#endif // DEPLOY_ISR_H
