// GolfIMU_Firmware.ino
// Teensy 4.0 + SparkFun BNO08x (BNO080/BNO085/BNO086) High-Performance IMU
// Backend-compatible version for BNO08x library version 1.0.6

#include <Wire.h>
#include <SparkFun_BNO08x_Arduino_Library.h>

BNO08x myIMU;

// Command handling
String inputString = "";
bool stringComplete = false;

// Mode settings
bool monitoringEnabled = false;
bool impactDetectionEnabled = false;  // Toggle for impact detection
bool testMode = true;                 // Test mode (no impact detection needed)

// Swing detection (only used if impactDetectionEnabled = true)
float impactThreshold = 30.0; // Default g-force threshold
unsigned long lastImpactTime = 0;
const unsigned long IMPACT_COOLDOWN_MS = 1000; // 1 second cooldown

// Session configuration
String sessionId = "";
String userId = "";
String clubId = "";
float clubLength = 1.07;
float clubMass = 0.205;

// IMU data storage
float currentAx = 0, currentAy = 0, currentAz = 0;
float currentGx = 0, currentGy = 0, currentGz = 0;
float currentMx = 0, currentMy = 0, currentMz = 0;
float currentQw = 0, currentQx = 0, currentQy = 0, currentQz = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 5000) delay(10);
  Serial.println("GolfIMU Backend-Compatible Firmware");
  Serial.println("Version: 1.0.0");
  Serial.print("Test Mode: "); Serial.println(testMode ? "ENABLED" : "DISABLED");
  Serial.print("Impact Detection: "); Serial.println(impactDetectionEnabled ? "ENABLED" : "DISABLED");

  Wire.begin();
  Wire.setClock(400000);
  
  if (!myIMU.begin()) {
    Serial.println("BNO08x not detected. Check wiring!");
    while (1) delay(1000);
  }
  Serial.println("BNO08x connected!");

  // Enable all sensors
  myIMU.enableAccelerometer(1000);  // 1000Hz
  myIMU.enableGyro(1000);           // 1000Hz
  myIMU.enableMagnetometer();
  myIMU.enableRotationVector();
  
  Serial.println("Sensors enabled. Ready for backend connection.");
  Serial.println("Commands: CONFIG:, START_MONITORING, STOP_MONITORING, REQUEST_SWING");
  Serial.println("Mode Commands: ENABLE_IMPACT, DISABLE_IMPACT, TEST_MODE, PRODUCTION_MODE");
}

void loop() {
  // Handle incoming commands
  if (stringComplete) {
    handleCommand(inputString);
    inputString = "";
    stringComplete = false;
  }
  
  // Service the BNO08x bus and check for new data
  if (myIMU.serviceBus()) {
    if (myIMU.getSensorEvent()) {
      uint8_t sensorId = myIMU.getSensorEventID();
      
      // Update current sensor values
      if (sensorId == SH2_ACCELEROMETER) {
        currentAx = myIMU.getAccelX();
        currentAy = myIMU.getAccelY();
        currentAz = myIMU.getAccelZ();
      }
      else if (sensorId == SH2_GYROSCOPE_CALIBRATED) {
        currentGx = myIMU.getGyroX();
        currentGy = myIMU.getGyroY();
        currentGz = myIMU.getGyroZ();
      }
      else if (sensorId == SH2_MAGNETIC_FIELD_UNCALIBRATED) {
        currentMx = myIMU.getMagX();
        currentMy = myIMU.getMagY();
        currentMz = myIMU.getMagZ();
      }
      else if (sensorId == SH2_ROTATION_VECTOR) {
        currentQw = myIMU.getQuatI();
        currentQx = myIMU.getQuatJ();
        currentQy = myIMU.getQuatK();
        currentQz = myIMU.getQuatReal();
      }
      
      // Output combined IMU data (backend expects this format) - OPTIMIZED
      char jsonBuffer[256];
      snprintf(jsonBuffer, sizeof(jsonBuffer), 
        "{\"t\":%lu,\"ax\":%.3f,\"ay\":%.3f,\"az\":%.3f,\"gx\":%.3f,\"gy\":%.3f,\"gz\":%.3f,\"mx\":%.3f,\"my\":%.3f,\"mz\":%.3f,\"qw\":%.4f,\"qx\":%.4f,\"qy\":%.4f,\"qz\":%.4f}",
        millis(), currentAx, currentAy, currentAz, currentGx, currentGy, currentGz, 
        currentMx, currentMy, currentMz, currentQw, currentQx, currentQy, currentQz);
      Serial.println(jsonBuffer);
      
      // Check for impact only if monitoring and impact detection are enabled
      // DISABLED for maximum speed data collection
      // if (monitoringEnabled && impactDetectionEnabled) {
      //   checkForImpact();
      // }
    }
  }
}

void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    inputString += inChar;
    if (inChar == '\n') {
      stringComplete = true;
    }
  }
}

void handleCommand(String command) {
  command.trim();
  
  if (command.startsWith("CONFIG:")) {
    // Parse session configuration
    String configJson = command.substring(7); // Remove "CONFIG:" prefix
    // TODO: Parse JSON config and update session variables
    Serial.println("Config received: " + configJson);
  }
  else if (command == "START_MONITORING") {
    monitoringEnabled = true;
    Serial.println("Swing monitoring started");
    if (testMode) {
      Serial.println("Test mode: All swing data will be logged (no impact detection needed)");
    }
  }
  else if (command == "STOP_MONITORING") {
    monitoringEnabled = false;
    Serial.println("Swing monitoring stopped");
  }
  else if (command == "REQUEST_SWING") {
    // TODO: Send last swing data if available
    Serial.println("Swing data requested");
  }
  else if (command == "ENABLE_IMPACT") {
    impactDetectionEnabled = true;
    testMode = false;
    Serial.println("Impact detection ENABLED - Production mode");
  }
  else if (command == "DISABLE_IMPACT") {
    impactDetectionEnabled = false;
    testMode = true;
    Serial.println("Impact detection DISABLED - Test mode");
  }
  else if (command == "TEST_MODE") {
    testMode = true;
    impactDetectionEnabled = false;
    Serial.println("Test mode ENABLED - No impact detection needed");
  }
  else if (command == "PRODUCTION_MODE") {
    testMode = false;
    impactDetectionEnabled = true;
    Serial.println("Production mode ENABLED - Impact detection active");
  }
  else if (command == "STATUS") {
    Serial.print("Monitoring: "); Serial.println(monitoringEnabled ? "ON" : "OFF");
    Serial.print("Test Mode: "); Serial.println(testMode ? "ON" : "OFF");
    Serial.print("Impact Detection: "); Serial.println(impactDetectionEnabled ? "ON" : "OFF");
  }
  else {
    Serial.println("Unknown command: " + command);
    Serial.println("Available commands: CONFIG:, START_MONITORING, STOP_MONITORING, REQUEST_SWING");
    Serial.println("Mode commands: ENABLE_IMPACT, DISABLE_IMPACT, TEST_MODE, PRODUCTION_MODE, STATUS");
  }
}

void checkForImpact() {
  // Calculate total acceleration magnitude
  float accelMagnitude = sqrt(currentAx*currentAx + currentAy*currentAy + currentAz*currentAz);
  
  // Check if impact threshold is exceeded and cooldown has passed
  if (accelMagnitude > impactThreshold && (millis() - lastImpactTime) > IMPACT_COOLDOWN_MS) {
    lastImpactTime = millis();
    
    // TODO: Implement swing buffering and complete swing detection
    Serial.print("IMPACT_DETECTED: "); Serial.print(accelMagnitude, 1); Serial.println("g");
  }
}
