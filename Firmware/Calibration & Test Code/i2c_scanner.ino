#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_BMP085.h>
#include <QMC5883LCompass.h>

// Initialize sensor objects
Adafruit_BMP085 bmp;
QMC5883LCompass compass;

// Flags and variables
bool bmp_working = false;
const int I2C_SDA = 21;
const int I2C_SCL = 22;

// Function to scan the bus and return number of devices
int scanI2CBus() {
  Serial.println("--- Scanning I2C Bus ---");
  byte error, address;
  int nDevices = 0;
  
  // A standard I2C scanner helps determine if the hardware is electrically connected
  for(address = 1; address < 127; address++ ) {
    Wire.beginTransmission(address);
    error = Wire.endTransmission();
    
    if (error == 0) {
      Serial.print("Found device at 0x");
      if (address < 16) Serial.print("0");
      Serial.print(address, HEX);
      
      // Identify common addresses
      if (address == 0x77) Serial.println(" (Likely BMP180)");
      else if (address == 0x0D) Serial.println(" (Likely QMC5883L)");
      else Serial.println(" (Unknown Device)");
      
      nDevices++;
    } else if (error == 4) {
      Serial.print("Unknown error at address 0x");
      if (address < 16) Serial.print("0");
      Serial.println(address, HEX);
    }
  }
  return nDevices;
}

void setup() {
  Serial.begin(115200);
  delay(2000); // Give serial monitor time to connect

  // Initialize I2C with stability settings
  // Default for ESP32 DevKit V1 is SDA=21, SCL=22
  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(100000); // Standard 100kHz mode is safer for jumper wires
  Wire.setTimeOut(1000); // Timeout to prevent the CPU from hanging on a bad bus
  
  int devicesFound = scanI2CBus();
  
  if (devicesFound == 0) {
    Serial.println("ERROR: No I2C devices detected!");
    Serial.println("1. Check if 3.3V and GND are connected to both sensors.");
    Serial.println("2. Check if SDA is on Pin 21 and SCL is on Pin 22.");
    Serial.println("3. Ensure your soldering joints are making contact with the pads.");
  }

  Serial.println("\n--- Initializing Sensor Libraries ---");

  // BMP180 Initialization
  if (!bmp.begin()) {
    Serial.println("BMP180: FAILED to initialize library.");
    bmp_working = false;
  } else {
    Serial.println("BMP180: SUCCESS");
    bmp_working = true;
  }

  // QMC5883L Initialization
  compass.init();
  compass.setSmoothing(10, true);
  Serial.println("QMC5883L: Initialized (Note: init() does not check for presence)");
  
  Serial.println("----------------------------\n");
}

void loop() {
  Serial.println("========== SENSOR DATA ==========");
  
  // 1. Process BMP180
  if (bmp_working) {
    float temp = bmp.readTemperature();
    // Check for logical errors (extreme values)
    if (temp < -40 || temp > 80) {
       Serial.println("[BMP180]   Data Error: Reading out of range.");
    } else {
       Serial.print("[BMP180]   Temp: "); Serial.print(temp);
       Serial.print(" C | Pressure: "); Serial.print(bmp.readPressure()); Serial.println(" Pa");
    }
  } else {
    Serial.println("[BMP180]   OFFLINE (Initialization failed)");
  }

  // 2. Process QMC5883L
  compass.read();
  int x = compass.getX();
  int y = compass.getY();
  int z = compass.getZ();

  // If the compass returns all zeros, it is physically disconnected or the bus crashed
  if (x == 0 && y == 0 && z == 0) {
    Serial.println("[QMC5883L] OFFLINE (Returning all zeros)");
    
    // Attempt emergency bus recovery if we lost communication
    Serial.println("Attempting I2C Bus Reset...");
    Wire.end();
    delay(100);
    Wire.begin(I2C_SDA, I2C_SCL);
    Wire.setClock(100000);
  } else {
    Serial.print("[QMC5883L] X: "); Serial.print(x);
    Serial.print(" | Y: "); Serial.print(y);
    Serial.print(" | Z: "); Serial.print(z);
    Serial.print(" | Heading: "); Serial.print(compass.getAzimuth()); Serial.println("°");
  }

  Serial.println("=================================\n");
  delay(1000);
}