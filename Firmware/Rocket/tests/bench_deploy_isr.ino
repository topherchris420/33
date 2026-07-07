#include <Arduino.h>
#include "esp_timer.h"
#include "../src/deploy_isr.h"

void setup() {
    Serial.begin(115200);
    delay(2000);
    
    init_project_33_deploy_system();
    
    Serial.println("trial,requested_us,actual_us,jitter_us");
    
    for (int i = 0; i < 10000; i++) {
        uint64_t start = esp_timer_get_time();
        uint64_t delay_target_us = 50000; // 50ms
        trigger_deployment_sequence(delay_target_us);
        
        while (!is_fins_deployed()) {
            delayMicroseconds(10);
        }
        
        uint64_t actual = esp_timer_get_time() - start;
        uint64_t jitter = actual > delay_target_us ? actual - delay_target_us : delay_target_us - actual;
        
        Serial.printf("%d,%llu,%llu,%llu\n", i, delay_target_us, actual, jitter);
        
        // Reset state for next trial (note: in real flight, this is a one-shot)
        reset_fins_deployed();
        delay(10);
    }
}

void loop() {
    delay(1000);
}
