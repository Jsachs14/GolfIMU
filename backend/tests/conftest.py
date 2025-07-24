"""
Pytest configuration and fixtures for GolfIMU tests
"""
import pytest
import redis
from unittest.mock import Mock, MagicMock
from datetime import datetime
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from global_config import *
from backend.models import IMUData, SessionConfig, SwingEvent, ProcessedMetrics, RedisKey, SwingData
from backend.redis_manager import RedisManager
from backend.serial_manager import SerialManager
from backend.session_manager import SessionManager
from backend.config import Settings
from backend.main import GolfIMUBackend


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing"""
    mock_client = Mock(spec=redis.Redis)
    mock_client.lpush.return_value = 1
    mock_client.ltrim.return_value = True
    mock_client.lrange.return_value = []
    mock_client.set.return_value = True
    mock_client.get.return_value = None
    mock_client.delete.return_value = 1
    mock_client.llen.return_value = 0
    return mock_client


@pytest.fixture
def mock_serial_connection():
    """Mock serial connection for testing"""
    mock_serial = Mock()
    mock_serial.is_open = True
    # Return proper IMU data format for read_imu_data test (JSON format)
    mock_serial.readline.return_value = b'{"ax": 1.0, "ay": 2.0, "az": 3.0, "gx": 4.0, "gy": 5.0, "gz": 6.0, "mx": 7.0, "my": 8.0, "mz": 9.0, "qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0, "t": 1640995200000}\n'
    mock_serial.write.return_value = 10
    return mock_serial


@pytest.fixture
def sample_imu_data():
    """Sample IMU data for testing"""
    return IMUData(
        ax=1.0,
        ay=2.0,
        az=3.0,
        gx=4.0,
        gy=5.0,
        gz=6.0,
        mx=7.0,
        my=8.0,
        mz=9.0,
        qw=1.0,
        qx=0.0,
        qy=0.0,
        qz=0.0,
        timestamp=datetime.now()
    )


@pytest.fixture
def sample_swing_data(sample_imu_data):
    """Sample swing data for testing"""
    return SwingData(
        session_id="test_session",
        imu_data_points=[sample_imu_data],
        swing_start_time=datetime(2023, 1, 1, 12, 0, 0),
        swing_end_time=datetime(2023, 1, 1, 12, 0, 1),
        swing_duration=1.0,
        impact_g_force=30.0,
        swing_type="full_swing"
    )


@pytest.fixture
def sample_session_config():
    """Sample session configuration for testing"""
    return SessionConfig(
        user_id="test_user",
        club_id="driver",
        club_length=1.07,
        club_mass=0.205,
        face_normal_calibration=[1.0, 0.0, 0.0],
        impact_threshold=30.0
    )


@pytest.fixture
def sample_swing_event():
    """Sample swing event for testing"""
    return SwingEvent(
        session_id="test_session",
        event_type="impact",
        data={"g_force": 35.0}
    )


@pytest.fixture
def test_settings():
    """Test settings configuration"""
    return Settings(
        redis_host=REDIS_HOST,
        redis_port=REDIS_PORT,
        redis_db=TEST_REDIS_DB,  # Use different DB for testing
        serial_port=TEST_SERIAL_PORT,
        serial_baudrate=SERIAL_BAUDRATE,
        imu_sample_rate=TEST_IMU_SAMPLE_RATE,
        buffer_size=100
    )


@pytest.fixture
def redis_manager_with_mock(mock_redis_client, monkeypatch):
    """Redis manager with mocked Redis client"""
    manager = RedisManager()
    monkeypatch.setattr(manager, 'redis_client', mock_redis_client)
    return manager


@pytest.fixture
def serial_manager_with_mock(mock_serial_connection, monkeypatch):
    """Serial manager with mocked serial connection"""
    manager = SerialManager()
    monkeypatch.setattr(manager, 'serial_connection', mock_serial_connection)
    monkeypatch.setattr(manager, 'is_connected', True)
    return manager


@pytest.fixture
def session_manager_with_mock(redis_manager_with_mock):
    """Session manager with mocked Redis manager"""
    return SessionManager(redis_manager_with_mock)


@pytest.fixture
def mock_session():
    """Mock session object for testing"""
    mock = Mock()
    mock.session_id = "test_session"
    mock.user_id = "test_user"
    mock.club_id = "driver"
    mock.impact_threshold = 30.0
    return mock


@pytest.fixture
def mock_session_with_impact_threshold():
    """Mock session with impact threshold for testing"""
    mock = Mock()
    mock.session_id = "test_session"
    mock.user_id = "test_user"
    mock.club_id = "driver"
    mock.impact_threshold = 30.0
    return mock


@pytest.fixture
def backend_with_mocks(monkeypatch):
    """GolfIMUBackend with mocked dependencies"""
    backend = GolfIMUBackend()
    return backend


@pytest.fixture
def backend_with_session(backend_with_mocks, mock_session):
    """GolfIMUBackend with mocked session"""
    backend = backend_with_mocks
    backend.session_manager.get_current_session = Mock(return_value=mock_session)
    return backend


@pytest.fixture
def backend_with_arduino_connected(backend_with_mocks):
    """GolfIMUBackend with mocked Arduino connection"""
    backend = backend_with_mocks
    backend.serial_manager.is_connected = True
    backend.serial_manager.get_connection_status = Mock(return_value=(True, "/dev/tty.test"))
    return backend


@pytest.fixture
def backend_with_session_and_arduino(backend_with_session, backend_with_arduino_connected):
    """GolfIMUBackend with both session and Arduino connection"""
    backend = backend_with_session
    backend.serial_manager.is_connected = True
    backend.serial_manager.get_connection_status = Mock(return_value=(True, "/dev/tty.test"))
    return backend


@pytest.fixture
def mock_process():
    """Mock subprocess for C program testing"""
    mock = Mock()
    mock.poll.return_value = None  # Process is running
    mock.terminate.return_value = None
    mock.wait.return_value = 0
    return mock


@pytest.fixture
def mock_process_that_stops():
    """Mock subprocess that stops after a few iterations"""
    mock = Mock()
    call_count = 0
    def mock_poll():
        nonlocal call_count
        call_count += 1
        return None if call_count < 3 else 0  # Stop after 3 iterations
    mock.poll.side_effect = mock_poll
    mock.terminate.return_value = None
    mock.wait.return_value = 0
    return mock


@pytest.fixture
def mock_file_with_imu_data():
    """Mock file with IMU data for testing"""
    mock_file = Mock()
    mock_file.readlines.return_value = ['{"ax": 1.0, "ay": 2.0, "az": 3.0, "gx": 4.0, "gy": 5.0, "gz": 6.0, "mx": 7.0, "my": 8.0, "mz": 9.0, "qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0, "t": 1640995200000}\n']
    return mock_file


@pytest.fixture
def mock_file_empty():
    """Mock empty file for testing"""
    mock_file = Mock()
    mock_file.readlines.return_value = []
    return mock_file


@pytest.fixture
def high_g_force_imu_data():
    """IMU data with high acceleration for impact testing"""
    return IMUData(
        ax=294.3,  # High acceleration in m/s² (about 30g)
        ay=0.0, az=0.0,
        gx=0.0, gy=0.0, gz=0.0,
        mx=0.0, my=0.0, mz=0.0,
        qw=1.0, qx=0.0, qy=0.0, qz=0.0
    )


@pytest.fixture
def low_g_force_imu_data():
    """IMU data with low acceleration for impact testing"""
    return IMUData(
        ax=10.0,  # Low acceleration in m/s² (about 1g)
        ay=0.0, az=0.0,
        gx=0.0, gy=0.0, gz=0.0,
        mx=0.0, my=0.0, mz=0.0,
        qw=1.0, qx=0.0, qy=0.0, qz=0.0
    ) 