/*
 * Project 33: Zero-Blocking Fin Deployment ISR
 * Vers3Dynamics
 *
 * Refactored from ZeroBlockingFinDeploy.cpp into a reusable
 * compilation unit for the Rocket PlatformIO build.
 */

#include "deploy_isr.h"
#include <Arduino.h>
#include "esp_timer.h"
#include "driver/gpio.h"

// GPIO 33 is free on the rocket board; GPIO 5 (the previous choice) is the
// ignition servo PWM pin, and driving it from the deploy ISR corrupted the
// servo signal. Keep this pin clear of every assignment in docs/WIRING.md.
const int DEPLOY_OUTPUT_PIN = 33;
const float DEPLOY_ACCEL_THRESHOLD_G = 15.0;
const float DEPLOY_ACCEL_THRESHOLD_MS2 = DEPLOY_ACCEL_THRESHOLD_G * 9.80665f;
static const gpio_num_t DEPLOY_GPIO = (gpio_num_t)DEPLOY_OUTPUT_PIN;
static volatile bool fins_deployed = false;
static esp_timer_handle_t deploy_timer = nullptr;

void IRAM_ATTR on_deploy_timer_callback(void* arg) {
    gpio_set_level(DEPLOY_GPIO, 1);
    fins_deployed = true;
}

void init_project_33_deploy_system() {
    gpio_config_t io_conf = {};
    io_conf.pin_bit_mask = (1ULL << DEPLOY_GPIO);
    io_conf.mode = GPIO_MODE_OUTPUT;
    io_conf.pull_up_en = GPIO_PULLUP_DISABLE;
    io_conf.pull_down_en = GPIO_PULLDOWN_DISABLE;
    io_conf.intr_type = GPIO_INTR_DISABLE;
    gpio_config(&io_conf);
    gpio_set_level(DEPLOY_GPIO, 0);

    esp_timer_create_args_t timer_args = {};
    timer_args.callback = &on_deploy_timer_callback;
    timer_args.name = "fin_deploy_timer";

    if (esp_timer_create(&timer_args, &deploy_timer) != ESP_OK) {
        Serial.println("ERROR: Failed to create deploy timer");
        return;
    }
}

void trigger_deployment_sequence(uint64_t delay_us) {
    if (!fins_deployed && deploy_timer != nullptr) {
        esp_timer_start_once(deploy_timer, delay_us);
    }
}

bool is_fins_deployed() {
    return fins_deployed;
}

void reset_fins_deployed() {
    fins_deployed = false;
}
