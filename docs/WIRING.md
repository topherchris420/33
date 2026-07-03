# Wiring Reference

Pin assignments are aligned with the current firmware constants in `Firmware/Rocket/src/main.cpp` and `Firmware/Launcher/src/main.cpp`.

---

## Rocket Flight Computer (ESP32 DevKit V1)

### Servo Connections
| Function       | GPIO Pin | Servo Position |
|----------------|----------|----------------|
| Left Canard    | 26       | Left side      |
| Right Canard   | 25       | Right side     |
| Up Canard      | 27       | Top            |
| Down Canard    | 14       | Bottom         |
| Ignition Servo | 5        | Motor bay      |

### Servo Center Calibration
| Servo | Center Angle | Max Deflection |
|-------|--------------|----------------|
| Left  | 115°         | ±12°           |
| Right | 80°          | ±12°           |
| Up    | 80°          | ±12°           |
| Down  | 115°         | ±12°           |

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

### I2C Bus (QMC5883L, BMP180)
| Signal | GPIO Pin |
|--------|----------|
| SDA    | 21       |
| SCL    | 22       |

### I2C Device Addresses
| Device    | Address |
|-----------|---------|
| QMC5883L  | 0x0D    |
| BMP180    | 0x77    |

### GPS Module (Serial1)
| Signal | GPIO Pin | Baud Rate |
|--------|----------|-----------|
| RX1    | 4        | 9600      |

> GPS TX connects to the launcher ESP32 RX1 input on GPIO 4. The firmware ignores GPS TX by passing `-1` for the ESP32 transmit pin.

### UART to Rocket (Serial2)
| Signal | GPIO Pin | Baud Rate |
|--------|----------|-----------|
| TX2    | 17       | 115200    |
| RX2    | 16       | 115200    |

### Control Switches & Indicators
| Function       | GPIO Pin | Type               | Notes                     |
|----------------|----------|--------------------|---------------------------|
| Arm Switch     | 5        | Toggle Switch      | INPUT_PULLUP, active LOW  |
| Launch Button  | 18       | Momentary (N.O.)   | INPUT_PULLUP, active LOW  |
| Status LED     | 23       | LED                | HIGH = on                 |
| Buzzer         | 2        | Active Buzzer      | LOW-trigger               |
| Ignition Servo | 19       | SG90 Micro Servo   | Launcher-side interlock   |

### WiFi Configuration
| Parameter  | Value                 |
|------------|-----------------------|
| Mode       | SoftAP (Access Point) |
| SSID       | `ROCKET_LAUNCHER`     |
| Password   | `launch_secure`       |
| IP Address | 192.168.4.1           |
| UDP Port   | 4444                  |

---

## Dashboard (Python)

Connects to the launcher's WiFi AP and communicates with the launcher over UDP.

| Parameter    | Value       |
|--------------|-------------|
| Listen IP    | 0.0.0.0     |
| Listen Port  | 4444        |
| Launcher IP  | 192.168.4.1 |

### Link Layers
| Link | Transport | Purpose |
|------|-----------|---------|
| Dashboard -> Launcher | UDP/4444 over WiFi | Commands and PID tuning |
| Launcher -> Dashboard | UDP/4444 over WiFi | Telemetry relay, environment data, fusion status |
| Launcher <-> Rocket | UART2, 115200 baud | Rocket arming, ignition command, rocket telemetry |

### Dashboard UDP Protocol

The generated protocol reference is [PROTOCOL.md](PROTOCOL.md).
| Direction | Format | Example |
|-----------|--------|---------|
| Launcher -> Dashboard | `T,<ms>,<roll>,<rate>,<output>` | `T,1234,5.2,-3.1,4` |
| Launcher -> Dashboard | `STATUS:<state>,<Kp>,<Kd>,<skew>` | `STATUS:FLIGHT,0.5,0.2,1.3` |
| Launcher -> Dashboard | `ENV,<lat>,<lon>,<alt>,<gps_state>` | `ENV,34.1467,-118.3885,200.5,2` |
| Launcher -> Dashboard | `[FUSION] Hdg: <deg> \| Pitch: <deg>` | `[FUSION] Hdg: 104.5 \| Pitch: +02.1` |
| Dashboard -> Launcher | `HELLO` | `HELLO` |
| Dashboard -> Launcher | `PID,<Kp>,<Kd>` | `PID,0.8,0.3` |
| Dashboard -> Launcher | `launch` | `launch` |
| Dashboard -> Launcher | `calibrate` | `calibrate` |

### Rocket UART Protocol
| Direction | Format | Example |
|-----------|--------|---------|
| Rocket -> Launcher | `READY` | `READY` |
| Rocket -> Launcher | `IGNITED` | `IGNITED` |
| Rocket -> Launcher | `DATA,<ax>,<ay>,<az>,<roll>,<rate>,<output>,<state>,<Kp>,<Kd>,<skew>` | `DATA,0.02,0.10,9.78,5.2,-3.1,4,FLIGHT,0.50,0.20,1.3` |
| Launcher -> Rocket | `ARM` | `ARM` |
| Launcher -> Rocket | `IGNITE` | `IGNITE` |
| Launcher -> Rocket | `CALIBRATE` | `CALIBRATE` |
| Launcher -> Rocket | `PID,<Kp>,<Kd>` | `PID,0.8,0.3` |

### GPS State Codes
| Code | Meaning |
|------|---------|
| 0 | No NMEA data received |
| 1 | NMEA data received, no valid fix yet |
| 2 | Valid GPS fix acquired |
