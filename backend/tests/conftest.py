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
    mock_serial.readline.return_value = b'{"ax": 1.0, "ay": 2.0, "az": 3.0, "gx": 4.0, "gy": 5.0, "gz": 6.0, "mx": 7.0, "my": 8.0, "mz": 9.0, "t": 1640995200000}\n'
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