# Wiring Reference

Pin assignments reverse-engineered from the firmware source code.

---

## Rocket Flight Computer (ESP32 DevKit V1)

### Servo Connections
| Function       | GPIO Pin | Servo Position |
|----------------|----------|----------------|
| Left Canard    | 26       | Left side      |
| Right Canard   | 25       | Right side     |
| Up Canard      | 27       | Top            |
| Down Canard    | 14       | Bottom         |
| Ignition Servo | 13       | Motor bay      |

### Servo Center Calibration (from firmware defaults)
| Servo | Center Angle | Max Deflection |
|-------|-------------|----------------|
| Left  | 115°        | ±15°           |
| Right | 80°         | ±15°           |
| Up    | 80°         | ±15°           |
| Down  | 115°        | ±15°           |

### I2C Bus (MPU6050)
| Signal | GPIO Pin |
|--------|----------|
| SDA    | 21       |
| SCL    | 22       |

### UART to Launcher
| Signal | GPIO Pin | Baud Rate |
|--------|----------|-----------|
| TX2    | 17       | 115200    |
| RX2    | 16       | 115200    |

---

## Launcher Ground Station (ESP32 DevKit V1)

### I2C Bus (shared by MPU6050, QMC5883L, BMP180)
| Signal | GPIO Pin |
|--------|----------|
| SDA    | 21       |
| SCL    | 22       |

### I2C Device Addresses
| Device    | Address |
|-----------|---------|
| MPU6050   | 0x68    |
| QMC5883L  | 0x0D    |
| BMP180    | 0x77    |

### GPS Module (Serial1)
| Signal | GPIO Pin | Baud Rate |
|--------|----------|-----------|
| RX1    | 34       | 9600      |

> Note: GPS TX connects to ESP32 RX1 (pin 34). Pin 34 is input-only on ESP32.

### UART to Rocket (Serial2)
| Signal | GPIO Pin | Baud Rate |
|--------|----------|-----------|
| TX2    | 17       | 115200    |
| RX2    | 16       | 115200    |

### Control Switches & Indicators
| Function      | GPIO Pin | Type              | Notes                  |
|---------------|----------|-------------------|------------------------|
| Arm Switch    | 15       | Toggle Switch     | HIGH = armed           |
| Launch Button | 4        | Momentary (N.O.)  | INPUT_PULLUP, active LOW |
| Status LED    | 2        | LED (5mm)         | Onboard or external   |
| Buzzer        | 5        | Active Buzzer     | LOW-trigger            |
| Ignition Servo| 13       | SG90 Micro Servo  | Launcher-side ignition |

### WiFi Configuration
| Parameter  | Value              |
|------------|--------------------|
| Mode       | SoftAP (Access Point) |
| SSID       | `ROCKET_LAUNCHER`  |
| Password   | `launchpad1`       |
| IP Address | 192.168.4.1        |
| UDP Port   | 4444               |

---

## Dashboard (Python)

Connects to the launcher's WiFi AP and communicates via UDP.

| Parameter    | Value         |
|--------------|---------------|
| Listen IP    | 0.0.0.0       |
| Listen Port  | 4444          |
| Launcher IP  | 192.168.4.1   |

### Telemetry Protocol (UDP ASCII)
| Direction       | Format                              | Example                    |
|-----------------|-------------------------------------|----------------------------|
| Rocket → PC     | `T,<ms>,<roll>,<rate>,<output>`     | `T,1234,5.2,-3.1,4`       |
| Rocket → PC     | `STATUS:<state>,<Kp>,<Kd>,<skew>`   | `STATUS:FLIGHT,0.5,0.2,1.3` |
| Launcher → PC   | `ENV,<lat>,<lon>,<alt>,<gps_state>` | `ENV,34.1467,-118.3885,200.5,2` |
| PC → Rocket     | `PID,<Kp>,<Kd>`                     | `PID,0.8,0.3`              |
| PC → Rocket     | `launch`                            | `launch`                   |
| PC → Rocket     | `calibrate`                         | `calibrate`                |
