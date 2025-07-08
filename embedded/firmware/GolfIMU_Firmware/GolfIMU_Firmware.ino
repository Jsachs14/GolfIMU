// GolfIMU_Firmware.ino
// Teensy 4.0 + SparkFun BNO08x (BNO080/BNO085/BNO086) High-Performance IMU
// Maximum sample rate with delta time loop for optimal performance

#include <Wire.h>
#include <SparkFun_BNO08x_Arduino_Library.h>
#include "global_config.h"

BNO08x myIMU;

// Timing variables for delta time loop
unsigned long lastPrintTime = 0;
unsigned long sampleCount = 0;
unsigned long startTime = 0;

void setup() {
  Serial.begin(SERIAL_BAUDRATE);
  while (!Serial && millis() < SERIAL_WAIT_TIMEOUT_MS) delay(10);
  Serial.println(FIRMWARE_NAME);
  Serial.print("Version: "); Serial.println(FIRMWARE_VERSION);
  Serial.print("Sample Rate: "); Serial.print(IMU_SAMPLE_RATE_HZ); Serial.println("Hz (Maximum)");

  Wire.begin();
  Wire.setClock(WIRE_CLOCK_SPEED);
  
  if (!myIMU.begin()) {
    Serial.println(ERROR_IMU_NOT_DETECTED);
    while (1) delay(1000);
  }
  Serial.println("BNO08x connected!");

  // Enable all basic reports with maximum performance settings
  // Accelerometer: 1000Hz, ±16g range (maximum for golf swing analysis)
  myIMU.enableReport(BNO08x::SENSOR_REPORT_ACCELEROMETER, IMU_ACCEL_REPORT_RATE, IMU_ACCEL_RANGE_G);
  
  // Gyroscope: 1000Hz, ±2000 dps range (maximum for precise rotation detection)
  myIMU.enableReport(BNO08x::SENSOR_REPORT_GYROSCOPE, IMU_GYRO_REPORT_RATE, IMU_GYRO_RANGE_DPS);
  
  // Magnetometer: Default settings (typically 20Hz, sufficient for orientation)
  myIMU.enableReport(BNO08x::SENSOR_REPORT_MAGNETIC_FIELD);
  
  // Rotation Vector: Default settings (typically 100Hz, sufficient for quaternion)
  myIMU.enableReport(BNO08x::SENSOR_REPORT_ROTATION_VECTOR);
  
  startTime = millis();
  lastPrintTime = millis();
  Serial.print("High-performance IMU sampling started at "); Serial.print(IMU_SAMPLE_RATE_HZ); Serial.println("Hz");
}

void loop() {
  if (myIMU.dataAvailable()) {
    // Read all sensor data
    float ax = myIMU.getAccelX();
    float ay = myIMU.getAccelY();
    float az = myIMU.getAccelZ();
    float gx = myIMU.getGyroX();
    float gy = myIMU.getGyroY();
    float gz = myIMU.getGyroZ();
    float mx = myIMU.getMagX();
    float my = myIMU.getMagY();
    float mz = myIMU.getMagZ();
    float qw = myIMU.getQuatI();
    float qx = myIMU.getQuatJ();
    float qy = myIMU.getQuatK();
    float qz = myIMU.getQuatReal();

    // Delta time loop: only print at specified interval
    unsigned long currentTime = millis();
    if (currentTime - lastPrintTime >= PRINT_INTERVAL_MS) {
      // Print as JSON for backend (optimized format)
      Serial.print("{\"" JSON_TIME_FIELD "\":"); Serial.print(currentTime);
      Serial.print(",\"ax\":"); Serial.print(ax, JSON_FLOAT_PRECISION);
      Serial.print(",\"ay\":"); Serial.print(ay, JSON_FLOAT_PRECISION);
      Serial.print(",\"az\":"); Serial.print(az, JSON_FLOAT_PRECISION);
      Serial.print(",\"gx\":"); Serial.print(gx, JSON_FLOAT_PRECISION);
      Serial.print(",\"gy\":"); Serial.print(gy, JSON_FLOAT_PRECISION);
      Serial.print(",\"gz\":"); Serial.print(gz, JSON_FLOAT_PRECISION);
      Serial.print(",\"mx\":"); Serial.print(mx, JSON_FLOAT_PRECISION);
      Serial.print(",\"my\":"); Serial.print(my, JSON_FLOAT_PRECISION);
      Serial.print(",\"mz\":"); Serial.print(mz, JSON_FLOAT_PRECISION);
      Serial.print(",\"qw\":"); Serial.print(qw, JSON_QUAT_PRECISION);
      Serial.print(",\"qx\":"); Serial.print(qx, JSON_QUAT_PRECISION);
      Serial.print(",\"qy\":"); Serial.print(qy, JSON_QUAT_PRECISION);
      Serial.print(",\"qz\":"); Serial.print(qz, JSON_QUAT_PRECISION);
      Serial.println("}");
      
      lastPrintTime = currentTime;
      sampleCount++;
      
      // Print status every N samples
      if (sampleCount % SAMPLE_COUNT_REPORT == 0) {
        unsigned long elapsed = currentTime - startTime;
        float actualRate = (sampleCount * 1000.0) / elapsed;
        Serial.print("Status: "); Serial.print(sampleCount); 
        Serial.print(" samples, "); Serial.print(actualRate, 1); 
        Serial.println(" Hz actual rate");
      }
    }
  }
}
