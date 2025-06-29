# GolfIMU Setup Guide

This guide explains how to set up and run the GolfIMU backend system.

## Prerequisites

- Python 3.9 or higher
- pip (Python package installer)
- Git (for version control)
- Redis server (for data storage)

## Initial Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd GolfIMU
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
```

### 3. Activate Virtual Environment
**On macOS/Linux:**
```bash
source venv/bin/activate
```

**On Windows:**
```bash
venv\Scripts\activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Setup Redis (IMPORTANT for Data Persistence)

#### Install Redis
**On macOS:**
```bash
brew install redis
```

**On Ubuntu/Debian:**
```bash
sudo apt-get install redis-server
```

**On Windows:**
Download from https://redis.io/download

#### Configure Redis for Persistent Storage
To ensure your golf swing data survives computer restarts:

1. **Use the provided Redis config:**
```bash
# Start Redis with persistent storage
redis-server redis.conf
```

2. **Or configure manually:**
```bash
# Edit Redis config (usually /etc/redis/redis.conf)
# Add these lines:
save 60 1
save 300 10
save 900 100
appendonly yes
appendfsync everysec
```

3. **Test Redis persistence:**
```bash
# Start Redis
redis-server

# In another terminal, test connection
redis-cli ping
# Should return: PONG
```

**⚠️ IMPORTANT:** Without Redis persistence configured, your swing data will be lost when you restart your computer!

## Running Tests

### Run All Tests
```bash
python -m pytest backend/tests/ -v
```

### Run Specific Test Files
```bash
# Run only main backend tests
python -m pytest backend/tests/test_main.py -v

# Run only Redis manager tests
python -m pytest backend/tests/test_redis_manager.py -v

# Run only session manager tests
python -m pytest backend/tests/test_session_manager.py -v
```

### Run Tests with Coverage
```bash
python -m pytest backend/tests/ --cov=backend --cov-report=html
```

### Run Tests with Short Output
```bash
python -m pytest backend/tests/ --tb=short
```

## Running the Backend

### 1. Start Redis (if not already running)
```bash
redis-server redis.conf
```

### 2. Start the Backend
```bash
python backend/run_backend.py
```

### Available Commands in Backend
Once the backend is running, you can use these commands:
- `start_session <user_id> <club_id> <club_length> <club_mass>` - Start a new session
- `connect_arduino [port]` - Connect to Arduino (auto-detect if no port specified)
- `send_config` - Send session configuration to Arduino
- `start_monitoring` - Start swing monitoring
- `wait_swing` - Wait for swing data
- `continuous_monitoring` - Start continuous monitoring mode
- `status` - Show current status
- `summary` - Show session summary
- `statistics` - Show swing statistics
- `recent_swings [count]` - Show recent swings
- `quit` - Exit the backend

## Data Persistence

### What Data is Stored
- **Session Configurations**: User settings, club specifications
- **Swing Data**: Complete IMU readings for each swing
- **Swing Events**: Impact detection, swing timing
- **IMU Buffers**: Real-time sensor data

### Data Location
With Redis persistence enabled, data is stored in:
- **RDB file**: `dump.rdb` (snapshot of data)
- **AOF file**: `golfimu.aof` (append-only log of all operations)

### Data Recovery
Your data will survive:
- ✅ Computer restarts
- ✅ Redis server restarts
- ✅ Application crashes
- ✅ Power outages

### Backup Data
To backup your golf data:
```bash
# Copy Redis data files
cp dump.rdb golfimu_backup.rdb
cp golfimu.aof golfimu_backup.aof
```

## Configuration

### Environment Variables
Create a `.env` file in the project root to override default settings:

```env
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_password

# Serial Configuration
SERIAL_PORT=/dev/tty.usbserial-*
SERIAL_BAUDRATE=115200
SERIAL_TIMEOUT=1.0

# Data Processing
IMU_SAMPLE_RATE=200
BUFFER_SIZE=1000

# Session Management
DEFAULT_IMPACT_THRESHOLD=30.0
```

## Development Setup

### Project Structure
```
GolfIMU/
├── backend/
│   ├── main.py              # Main backend application
│   ├── models.py            # Data models
│   ├── config.py            # Configuration settings
│   ├── redis_manager.py     # Redis data management
│   ├── serial_manager.py    # Arduino serial communication
│   ├── session_manager.py   # Session management
│   ├── run_backend.py       # Backend runner script
│   └── tests/               # Test files
│       ├── test_main.py
│       ├── test_models.py
│       ├── test_config.py
│       ├── test_redis_manager.py
│       ├── test_serial_manager.py
│       ├── test_session_manager.py
│       └── conftest.py
├── redis.conf               # Redis persistence configuration
├── requirements.txt         # Python dependencies
├── SETUP.md               # This file
└── README.md              # Project documentation
```

### Adding New Tests
1. Create a new test file in `backend/tests/`
2. Follow the naming convention: `test_<module_name>.py`
3. Use pytest fixtures from `conftest.py` when possible
4. Run tests to ensure they pass

### Adding New Backend Features
1. Add new modules to the `backend/` directory
2. Update imports in `main.py` if needed
3. Add corresponding tests in `backend/tests/`
4. Update this setup guide with new instructions

## Troubleshooting

### Common Issues

**Virtual Environment Issues:**
- If you get permission errors, try: `python3 -m venv venv --user`
- If activation doesn't work, try: `source venv/bin/activate` (macOS/Linux) or `venv\Scripts\activate` (Windows)

**Import Errors:**
- Make sure you're in the project root directory
- Ensure the virtual environment is activated
- Check that all dependencies are installed: `pip install -r requirements.txt`

**Redis Issues:**
- **Redis not running**: Start with `redis-server redis.conf`
- **Connection refused**: Check if Redis is running on port 6379
- **Data lost after restart**: Ensure Redis persistence is configured
- **Permission denied**: Check Redis file permissions

**Test Failures:**
- Check that Redis is running (if tests require it)
- Ensure all dependencies are up to date
- Run tests with verbose output: `python -m pytest backend/tests/ -v`

**Backend Connection Issues:**
- Verify Arduino is connected and recognized
- Check serial port permissions
- Ensure correct baud rate settings

**Data Persistence Issues:**
- Check Redis logs: `tail -f redis.log`
- Verify Redis config: `redis-cli config get save`
- Test persistence: Add data, restart Redis, check if data remains

## Future Additions

This section will be updated as new features are added to the project.

### Planned Features
- [ ] Web API interface
- [ ] Real-time data visualization
- [ ] Swing analysis algorithms
- [ ] User authentication system
- [ ] Database integration
- [ ] Mobile app support
- [ ] Cloud data synchronization
- [ ] Advanced data analytics

### Development Workflow
1. Create feature branch: `git checkout -b feature/new-feature`
2. Implement changes
3. Add/update tests
4. Run test suite: `python -m pytest backend/tests/ -v`
5. Update documentation
6. Create pull request

---

**Last Updated:** $(date)
**Version:** 1.0.0 