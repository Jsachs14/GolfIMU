# 🏌️ GolfIMU

> **Advanced Golf Swing Analysis System**  
> Real-time IMU-based golf swing tracking and analysis with Kalman filtering

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![Redis](https://img.shields.io/badge/Redis-5.0+-red.svg)](https://redis.io)
[![Tests](https://img.shields.io/badge/Tests-172%20passed%20✅-green.svg)](https://github.com/Jsachs14/GolfIMU)
[![Coverage](https://img.shields.io/badge/Coverage-95%25-brightgreen.svg)](https://github.com/Jsachs14/GolfIMU)

---

## 🎯 Overview

GolfIMU is a sophisticated golf swing analysis system that combines embedded sensors, real-time data processing, and advanced algorithms to help golfers improve their game. The system uses 9-DOF IMU sensors to capture complete swing data and applies Kalman filtering for precise motion analysis.

### ✨ Key Features

- **🔄 Complete Swing Capture** - Full swing data with all IMU readings
- **🧠 Advanced Analytics** - Kalman filtering and Madgwick sensor fusion
- **📊 Real-time Metrics** - Club head speed, tempo analysis, swing plane detection
- **💾 Persistent Storage** - Redis-based data persistence with session management
- **🎯 Impact Detection** - Configurable g-force threshold detection
- **📈 Quality Scoring** - Swing consistency and smoothness analysis

---

## 🏗️ System Architecture

### Embedded System (Arduino)
- **Radio Communication** - Wireless data transmission
- **IMU Processing** - 9-DOF sensor data acquisition
- **Power Management** - Battery level monitoring and optimization
- **Swing Detection** - Real-time impact detection and buffering
- **Data Transmission** - Complete swing data streaming

### Backend System (Python)
- **Data Processing** - Complete swing analysis and storage
- **Redis Database** - High-performance data persistence
- **Session Management** - User and club configuration tracking
- **Analytics Engine** - Advanced swing metrics calculation

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Redis Server
- Arduino IDE (for embedded code)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Jsachs14/GolfIMU.git
   cd GolfIMU
   ```

2. **Set up virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start Redis server**
   ```bash
   # macOS
   brew services start redis
   
   # Or use the provided config
   redis-server redis.conf
   ```

5. **Run the backend**
   ```bash
   python backend/run_backend.py
   ```

---

## 📊 Analytics Modules

### 🧭 Sensor Fusion
- **Madgwick/Kalman Filtering** - Advanced quaternion-based orientation tracking
- **9-DOF Processing** - Accelerometer, gyroscope, and magnetometer fusion
- **Rotation Matrix Calculations** - Real-time kinematic transformations

### ⏱️ Timing Analysis
- **Backswing Detection** - Automatic backswing peak identification
- **Tempo Calculation** - 3:1 backswing-to-downswing ratio analysis
- **Impact Timing** - Precise impact detection with configurable thresholds

### 💨 Speed & Power
- **Club Head Speed** - Real-time velocity calculations using rigid body kinematics
- **Peak G-Force** - Maximum acceleration tracking per swing
- **Centripetal Force** - Shaft loading analysis for structural insights

### 🎯 Path & Plane
- **Swing Plane Tilt** - Principal component analysis for plane detection
- **Attack Angle** - Vertical component analysis at impact
- **Club Path** - Horizontal direction tracking for draw/fade detection
- **Face Angle** - Calibrated face normal calculations

### 📈 Quality Metrics
- **Smoothness Scoring** - Integrated jerk analysis for swing quality
- **Consistency Analysis** - Historical comparison and trend detection
- **FFT Impact Analysis** - Frequency domain contact quality assessment

---

## 🛠️ Usage

### Backend Commands
Once the backend is running, use these commands:

| Command | Description |
|---------|-------------|
| `start_session <user_id> <club_id> <length> <mass>` | Start new golf session |
| `connect_arduino [port]` | Connect to Arduino (auto-detect) |
| `send_config` | Send session config to Arduino |
| `start_monitoring` | Begin swing monitoring |
| `wait_swing` | Wait for swing data |
| `continuous_monitoring` | Start continuous monitoring mode |
| `status` | Show current system status |
| `summary` | Display session summary |
| `statistics` | Show swing statistics |
| `recent_swings [count]` | Display recent swings |
| `quit` | Exit the backend |

### Example Session
```bash
# Start a session with a driver
start_session user123 driver 1.07 0.205

# Connect to Arduino
connect_arduino

# Send configuration
send_config

# Start monitoring
start_monitoring

# Wait for swing data
wait_swing
```

---

## 📁 Project Structure

```
GolfIMU/
├── backend/                    # Python backend system
│   ├── main.py                # Main application logic
│   ├── models.py              # Pydantic data models
│   ├── config.py              # Configuration management
│   ├── redis_manager.py       # Redis operations
│   ├── serial_manager.py      # Arduino communication
│   ├── session_manager.py     # Session management
│   ├── run_backend.py         # Backend runner
│   └── tests/                 # Comprehensive test suite
├── embedded/                  # Arduino code (future)
├── redis.conf                 # Redis configuration
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

---

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
python -m pytest backend/tests/ -v

# Run with coverage
python -m pytest backend/tests/ --cov=backend --cov-report=html

# Run specific test modules
python -m pytest backend/tests/test_main.py -v
python -m pytest backend/tests/test_redis_manager.py -v
```

**Test Results:** 172 tests passed, 95% code coverage ✅

---

## 🔧 Configuration

### Environment Variables
Create a `.env` file to customize settings:

```env
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Serial Configuration
SERIAL_PORT=/dev/tty.usbserial-*
SERIAL_BAUDRATE=115200

# Data Processing
IMU_SAMPLE_RATE=200
BUFFER_SIZE=1000

# Session Management
DEFAULT_IMPACT_THRESHOLD=30.0
```

---

## 📊 Data Persistence

### Redis Storage
- **Session Configurations** - User settings and club specifications
- **Complete Swing Data** - Full IMU readings with timestamps
- **Swing Events** - Impact detection and timing analysis
- **Processed Metrics** - Calculated analytics and statistics

### Data Recovery
Your data survives:
- ✅ Computer restarts
- ✅ Redis server restarts
- ✅ Application crashes
- ✅ Power outages

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---


---

## 🙏 Acknowledgments

- **Noah** - For being the reluctant golf partner who inspired this project (you better play ass)
- **Jonah** - For having a golf game that desperately needs fixing (fuck the hook)


