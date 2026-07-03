/**
 * ESP32 Rocket Fin Calibrator (FIXED)
 * * MAPPING:
 * A -> Servo 27 (UP)
 * B -> Servo 14 (DOWN)
 * C -> Servo 26 (RIGHT)
 * D -> Servo 25 (LEFT)
 */

#include <Arduino.h>
#include <ESP32Servo.h>

// -----------------------------------------------------------
// CONFIGURATION
// -----------------------------------------------------------
const int NUM_SERVOS = 4;

// Pin Definitions
const int PIN_UP    = 27;
const int PIN_DOWN  = 14;
const int PIN_RIGHT = 26;
const int PIN_LEFT  = 25;

// Arrays for easy indexing: 0=UP, 1=DOWN, 2=RIGHT, 3=LEFT
int servoPins[NUM_SERVOS] = {PIN_UP, PIN_DOWN, PIN_RIGHT, PIN_LEFT};
String servoNames[NUM_SERVOS] = {"UP (27)", "DOWN (14)", "RIGHT (26)", "LEFT (25)"};

// This array holds the live center angle for each servo
int centerAngles[NUM_SERVOS] = {90, 90, 90, 90};

// Track which servo is currently selected (Default to 0 / UP)
int activeIndex = 0; 

Servo servos[NUM_SERVOS];

// -----------------------------------------------------------
// FUNCTION PROTOTYPES (This fixes the error!)
// -----------------------------------------------------------
void printInstructions();
void printSelection();
void changeAngle(int amount);

// -----------------------------------------------------------
// SETUP
// -----------------------------------------------------------
void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);

  // Allocate timers
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);

  Serial.println("--- Rocket Fin Calibrator Started ---");

  // Attach all servos and move to initial 90
  for (int i = 0; i < NUM_SERVOS; i++) {
    servos[i].setPeriodHertz(50);
    servos[i].attach(servoPins[i]);
    servos[i].write(centerAngles[i]);
  }

  printInstructions();
}

// -----------------------------------------------------------
// LOOP
// -----------------------------------------------------------
void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    
    // Ignore newline/carriage return characters
    if (cmd == '\n' || cmd == '\r') return;

    // Convert lowercase a,b,c,d to uppercase
    cmd = toupper(cmd);

    // --- SELECTION LOGIC ---
    if (cmd == 'A') {
      activeIndex = 0;
      printSelection();
    }
    else if (cmd == 'B') {
      activeIndex = 1;
      printSelection();
    }
    else if (cmd == 'C') {
      activeIndex = 2;
      printSelection();
    }
    else if (cmd == 'D') {
      activeIndex = 3;
      printSelection();
    }
    // --- ADJUSTMENT LOGIC ---
    else if (cmd == '+') {
      changeAngle(1);
    }
    else if (cmd == '-') {
      changeAngle(-1);
    }
  }
}

// -----------------------------------------------------------
// HELPER FUNCTIONS
// -----------------------------------------------------------

void changeAngle(int amount) {
  // Update the angle for the CURRENTLY selected servo only
  centerAngles[activeIndex] += amount;

  // Safety limits (0 to 180)
  if (centerAngles[activeIndex] > 180) centerAngles[activeIndex] = 180;
  if (centerAngles[activeIndex] < 0)   centerAngles[activeIndex] = 0;

  // Move the servo
  servos[activeIndex].write(centerAngles[activeIndex]);

  // Print Update
  Serial.print(">>> Adjusted ");
  Serial.print(servoNames[activeIndex]);
  Serial.print(" | New Center: ");
  Serial.println(centerAngles[activeIndex]);
}

void printSelection() {
  Serial.print("\n>>> SELECTED: ");
  Serial.println(servoNames[activeIndex]);
  Serial.print("    Current Angle: ");
  Serial.println(centerAngles[activeIndex]);
  Serial.println("    Use '+' or '-' to adjust.");
}

void printInstructions() {
  Serial.println("----------------------------------------");
  Serial.println("Type 'A' -> Select UP (27)");
  Serial.println("Type 'B' -> Select DOWN (14)");
  Serial.println("Type 'C' -> Select RIGHT (26)");
  Serial.println("Type 'D' -> Select LEFT (25)");
  Serial.println("----------------------------------------");
  Serial.println("Then use '+' or '-' to adjust that servo.");
  Serial.println("----------------------------------------");
  
  // Select A by default on startup
  printSelection(); 
}