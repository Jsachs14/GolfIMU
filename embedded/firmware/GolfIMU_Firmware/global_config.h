/*
 * Global configuration constants for GolfIMU Arduino firmware
 * This file contains all configurable constants that can be changed in one place
 */

#ifndef GLOBAL_CONFIG_H
#define GLOBAL_CONFIG_H

// =============================================================================
// IMU CONFIGURATION
// =============================================================================

// IMU Sample Rate (Hz) - Maximum for BNO08x is 1000Hz
#define IMU_SAMPLE_RATE_HZ 1000

// IMU Sensor Ranges
#define IMU_ACCEL_RANGE_G 16.0f      // Accelerometer range in g-force (±16g for golf swings)
#define IMU_GYRO_RANGE_DPS 2000.0f   // Gyroscope range in degrees per second

// IMU Sensor Report Rates (Hz)
#define IMU_ACCEL_REPORT_RATE 1000   // Accelerometer report rate
#define IMU_GYRO_REPORT_RATE 1000    // Gyroscope report rate
#define IMU_MAG_REPORT_RATE 20       // Magnetometer report rate (default)
#define IMU_QUAT_REPORT_RATE 100     // Quaternion report rate (default)

// =============================================================================
// SERIAL COMMUNICATION
// =============================================================================

// Serial Configuration
#define SERIAL_BAUDRATE 115200
#define SERIAL_TIMEOUT 1000          // Timeout in milliseconds

// =============================================================================
// TIMING CONFIGURATION
// =============================================================================

// Delta Time Loop Configuration
#define PRINT_INTERVAL_MS 1          // 1ms = 1000Hz maximum rate
#define STATUS_REPORT_INTERVAL_MS 1000  // Status report every second
#define SAMPLE_COUNT_REPORT 1000     // Report sample count every N samples

// =============================================================================
// FIRMWARE CONFIGURATION
// =============================================================================

// Firmware Version
#define FIRMWARE_VERSION "1.0.0"
#define FIRMWARE_NAME "GolfIMU High Performance"

// Debug Configuration
#define DEBUG_MODE false             // Set to true for debug output
#define DEBUG_INTERVAL_MS 5000       // Debug output interval

// =============================================================================
// JSON OUTPUT CONFIGURATION
// =============================================================================

// JSON Precision
#define JSON_FLOAT_PRECISION 3       // Decimal places for accelerometer/gyro/mag
#define JSON_QUAT_PRECISION 4        // Decimal places for quaternions

// JSON Field Names
#define JSON_TIME_FIELD "t"
#define JSON_ACCEL_FIELDS {"ax", "ay", "az"}
#define JSON_GYRO_FIELDS {"gx", "gy", "gz"}
#define JSON_MAG_FIELDS {"mx", "my", "mz"}
#define JSON_QUAT_FIELDS {"qw", "qx", "qy", "qz"}

// =============================================================================
// ERROR HANDLING
// =============================================================================

// Error Timeouts
#define IMU_INIT_TIMEOUT_MS 5000     // IMU initialization timeout
#define SERIAL_WAIT_TIMEOUT_MS 10000 // Serial connection wait timeout

// Error Messages
#define ERROR_IMU_NOT_DETECTED "BNO08x not detected. Check wiring!"
#define ERROR_IMU_INIT_FAILED "BNO08x initialization failed!"
#define ERROR_SERIAL_NOT_READY "Serial not ready!"

// =============================================================================
// PERFORMANCE OPTIMIZATION
// =============================================================================

// Memory Management
#define MAX_JSON_BUFFER_SIZE 256     // Maximum JSON string buffer size
#define MAX_ERROR_MESSAGE_SIZE 128   // Maximum error message size

// Loop Optimization
#define LOOP_DELAY_MS 0              // No delay in main loop for maximum performance
#define WIRE_CLOCK_SPEED 400000      // I2C clock speed (400kHz for BNO08x)

#endif // GLOBAL_CONFIG_H 