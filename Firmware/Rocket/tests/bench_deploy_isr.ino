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
        uint64_t delay = 50000; // 50ms
        trigger_deployment_sequence(delay);
        
        while (!is_fins_deployed()) {
            delayMicroseconds(10);
        }
        
        uint64_t actual = esp_timer_get_time() - start;
        uint64_t jitter = actual > delay ? actual - delay : delay - actual;
        
        Serial.printf("%d,%llu,%llu,%llu\n", i, delay, actual, jitter);
        
        // Reset state for next trial (note: in real flight, this is a one-shot)
        extern volatile bool fins_deployed;
        fins_deployed = false;
        delay(10);
    }
}

void loop() {
    delay(1000);
}
