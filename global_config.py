"""
Global configuration constants for GolfIMU system
This file contains all configurable constants that can be changed in one place
"""

# =============================================================================
# IMU CONFIGURATION
# =============================================================================

# IMU Sample Rate (Hz) - Maximum for BNO08x is 1000Hz
IMU_SAMPLE_RATE_HZ = 1000

# IMU Sensor Ranges
IMU_ACCEL_RANGE_G = 16.0      # Accelerometer range in g-force (±16g for golf swings)
IMU_GYRO_RANGE_DPS = 2000.0   # Gyroscope range in degrees per second

# IMU Sensor Report Rates (Hz)
IMU_ACCEL_REPORT_RATE = 1000  # Accelerometer report rate
IMU_GYRO_REPORT_RATE = 1000   # Gyroscope report rate
IMU_MAG_REPORT_RATE = 20      # Magnetometer report rate (default)
IMU_QUAT_REPORT_RATE = 100    # Quaternion report rate (default)

# =============================================================================
# SERIAL COMMUNICATION
# =============================================================================

# Serial Configuration
SERIAL_BAUDRATE = 115200
SERIAL_TIMEOUT = 1.0
SERIAL_PORT_PATTERN = "/dev/tty.usbserial-*"  # Default for Mac

# =============================================================================
# DATA PROCESSING
# =============================================================================

# Buffer Configuration
IMU_BUFFER_SIZE = 1000        # Number of IMU samples to keep in ring buffer
SWING_BUFFER_SIZE = 100       # Number of swings to keep in memory

# Performance Optimization
IMU_TRIM_INTERVAL = 1000      # Only trim Redis buffer every N operations
IMU_MAX_BUFFER_SIZE = 50000   # Maximum IMU data points to keep in Redis
REDIS_BATCH_SIZE = 100        # Batch size for Redis operations

# Impact Detection
DEFAULT_IMPACT_THRESHOLD_G = 30.0  # Default g-force threshold for impact detection
MIN_IMPACT_THRESHOLD_G = 5.0       # Minimum allowed threshold
MAX_IMPACT_THRESHOLD_G = 100.0     # Maximum allowed threshold

# =============================================================================
# REDIS CONFIGURATION
# =============================================================================

# Redis Connection
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = None

# Redis Data Directory
REDIS_DATA_DIR = "./redis"

# Redis Persistence
REDIS_SAVE_INTERVALS = [
    (60, 1),    # Save every 60 seconds if at least 1 key changed
    (300, 10),  # Save every 300 seconds if at least 10 keys changed
    (900, 100)  # Save every 900 seconds if at least 100 keys changed
]

# =============================================================================
# SESSION MANAGEMENT
# =============================================================================

# Default Club Parameters
DEFAULT_CLUB_LENGTH_M = 1.07  # Default club length in meters
DEFAULT_CLUB_MASS_KG = 0.205  # Default club mass in kilograms

# Session Timeouts
SESSION_TIMEOUT_SECONDS = 3600  # 1 hour session timeout
SWING_TIMEOUT_SECONDS = 10      # 10 second swing timeout

# =============================================================================
# FIRMWARE CONFIGURATION
# =============================================================================

# Arduino/Teensy Configuration
TEENSY_BOARD = "teensy:avr:teensy40"  # Teensy 4.0 board
ARDUINO_CLI_TIMEOUT = 60              # Timeout for Arduino CLI operations

# Firmware Status Reporting
FIRMWARE_STATUS_INTERVAL_MS = 1000    # Status report interval in milliseconds
FIRMWARE_SAMPLE_COUNT_REPORT = 1000   # Report sample count every N samples

# =============================================================================
# SYSTEM CONFIGURATION
# =============================================================================

# Threading
COMMAND_PROCESSOR_SLEEP_MS = 10       # Sleep time for command processor thread
STATUS_UPDATE_INTERVAL_MS = 1000      # Status update interval
MONITORING_SLEEP_MS = 1               # Sleep time for monitoring loops

# Retry Logic
ARDUINO_CONNECT_MAX_RETRIES = 3       # Maximum Arduino connection retries
ARDUINO_CONNECT_RETRY_DELAY_MS = 2000 # Initial retry delay (doubles each retry)

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

# Log Levels
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = "golfimu_system.log"

# =============================================================================
# TESTING CONFIGURATION
# =============================================================================

# Test Settings
TEST_REDIS_DB = 1                     # Redis DB for testing (separate from production)
TEST_SERIAL_PORT = "/dev/tty.test"    # Mock serial port for testing
TEST_IMU_SAMPLE_RATE = 1000           # Sample rate for tests 