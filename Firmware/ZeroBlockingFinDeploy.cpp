/*
 * Project 33: Zero-Blocking Fin Deployment Interrupt
 * Vers3Dynamics
 */

#include <Arduino.h>
#include "esp_timer.h"
#include "driver/gpio.h"

static bool fins_deployed = false;
static esp_timer_handle_t deploy_timer;

// IRAM_ATTR ensures this runs from flash RAM, preventing interrupt latency
// caused by flash cache misses during high-speed execution.
void IRAM_ATTR on_deploy_timer_callback(void* arg) {
    // Hard GPIO toggle for deployment solenoid/pyro
    gpio_set_level(GPIO_NUM_5, 1); 
    fins_deployed = true;
}

void init_project_33_deploy_system() {
    // 1. Configure GPIO for ultra-fast, deterministic toggle
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << GPIO_NUM_5),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE // We are using a timer, not a pin interrupt
    };
    gpio_config(&io_conf);
    gpio_set_level(GPIO_NUM_5, 0); // Ensure safe state initially

    // 2. Create high-resolution hardware timer
    esp_timer_create_args_t timer_args = {
        .callback = &on_deploy_timer_callback,
        .name = "fin_deploy_timer"
    };
    
    if (esp_timer_create(&timer_args, &deploy_timer) != ESP_OK) {
        // Handle error in production environment
        return;
    }
}

// Call this function the exact microsecond the IMU detects muzzle egress (delta-V)
void trigger_deployment_sequence(uint64_t delay_us) {
    if (!fins_deployed) {
        // One-shot hardware timer. Completely ignores FreeRTOS scheduler.
        esp_timer_start_once(deploy_timer, delay_us); 
    }
}

void setup() {
    init_project_33_deploy_system();
    
    // Example: Simulating IMU detecting launch egress
    // In production, this is triggered by an IMU interrupt (e.g., >15g delta-V)
    delay(2000); 
    trigger_deployment_sequence(5000); // Deploy 5ms after egress trigger
}

void loop() {
    // Loop is now completely free for telemetry, canard control, or logging.
    // Fin deployment timing is 100% isolated from this loop.
    if (fins_deployed) {
        // Proceed with post-deployment flight logic
    }
}
