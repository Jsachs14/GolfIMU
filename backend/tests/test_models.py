"""
Tests for backend.models module
"""
import pytest
from datetime import datetime
from backend.models import IMUData, SessionConfig, SwingEvent, ProcessedMetrics, RedisKey


class TestIMUData:
    """Test IMUData model"""
    
    def test_imu_data_creation(self):
        """Test creating IMUData with all required fields"""
        imu_data = IMUData(
            ax=1.0, ay=2.0, az=3.0,
            gx=4.0, gy=5.0, gz=6.0,
            mx=7.0, my=8.0, mz=9.0
        )
        
        assert imu_data.ax == 1.0
        assert imu_data.ay == 2.0
        assert imu_data.az == 3.0
        assert imu_data.gx == 4.0
        assert imu_data.gy == 5.0
        assert imu_data.gz == 6.0
        assert imu_data.mx == 7.0
        assert imu_data.my == 8.0
        assert imu_data.mz == 9.0
        assert isinstance(imu_data.timestamp, datetime)
    
    def test_imu_data_with_custom_timestamp(self):
        """Test IMUData with custom timestamp"""
        custom_time = datetime(2023, 1, 1, 12, 0, 0)
        imu_data = IMUData(
            ax=1.0, ay=2.0, az=3.0,
            gx=4.0, gy=5.0, gz=6.0,
            mx=7.0, my=8.0, mz=9.0,
            timestamp=custom_time
        )
        
        assert imu_data.timestamp == custom_time
    
    def test_imu_data_validation(self):
        """Test IMUData field validation"""
        # Should accept float values
        imu_data = IMUData(
            ax=1.5, ay=-2.3, az=0.0,
            gx=10.5, gy=-5.2, gz=3.14,
            mx=25.0, my=-15.5, mz=8.9
        )
        
        assert isinstance(imu_data.ax, float)
        assert isinstance(imu_data.ay, float)
        assert isinstance(imu_data.az, float)


class TestSessionConfig:
    """Test SessionConfig model"""
    
    def test_session_config_creation(self):
        """Test creating SessionConfig with required fields"""
        session_config = SessionConfig(
            user_id="test_user",
            club_id="driver",
            club_length=1.07,
            club_mass=0.205
        )
        
        assert session_config.user_id == "test_user"
        assert session_config.club_id == "driver"
        assert session_config.club_length == 1.07
        assert session_config.club_mass == 0.205
        assert session_config.impact_threshold == 30.0  # default
        assert isinstance(session_config.session_id, str)
        assert isinstance(session_config.session_start_time, datetime)
    
    def test_session_config_with_optional_fields(self):
        """Test SessionConfig with optional fields"""
        face_normal = [1.0, 0.0, 0.0]
        session_config = SessionConfig(
            user_id="test_user",
            club_id="driver",
            club_length=1.07,
            club_mass=0.205,
            face_normal_calibration=face_normal,
            impact_threshold=25.0
        )
        
        assert session_config.face_normal_calibration == face_normal
        assert session_config.impact_threshold == 25.0
    
    def test_session_config_unique_ids(self):
        """Test that each SessionConfig gets unique session_id"""
        config1 = SessionConfig(
            user_id="user1", club_id="driver",
            club_length=1.07, club_mass=0.205
        )
        config2 = SessionConfig(
            user_id="user2", club_id="iron",
            club_length=0.95, club_mass=0.180
        )
        
        assert config1.session_id != config2.session_id
        assert len(config1.session_id) > 0
        assert len(config2.session_id) > 0


class TestSwingEvent:
    """Test SwingEvent model"""
    
    def test_swing_event_creation(self):
        """Test creating SwingEvent with required fields"""
        event = SwingEvent(
            session_id="test_session",
            event_type="impact"
        )
        
        assert event.session_id == "test_session"
        assert event.event_type == "impact"
        assert isinstance(event.swing_id, str)
        assert isinstance(event.timestamp, datetime)
        assert event.data is None
    
    def test_swing_event_with_data(self):
        """Test SwingEvent with additional data"""
        event_data = {"g_force": 35.0, "velocity": 45.2}
        event = SwingEvent(
            session_id="test_session",
            event_type="impact",
            data=event_data
        )
        
        assert event.data == event_data
    
    def test_swing_event_unique_ids(self):
        """Test that each SwingEvent gets unique swing_id"""
        event1 = SwingEvent(session_id="session1", event_type="start")
        event2 = SwingEvent(session_id="session2", event_type="impact")
        
        assert event1.swing_id != event2.swing_id


class TestProcessedMetrics:
    """Test ProcessedMetrics model"""
    
    def test_processed_metrics_creation(self):
        """Test creating ProcessedMetrics"""
        metrics = ProcessedMetrics(
            swing_id="test_swing",
            session_id="test_session"
        )
        
        assert metrics.swing_id == "test_swing"
        assert metrics.session_id == "test_session"
        assert isinstance(metrics.timestamp, datetime)
        assert metrics.metrics == {}
    
    def test_processed_metrics_with_data(self):
        """Test ProcessedMetrics with metric data"""
        metric_data = {
            "head_speed": 45.2,
            "tempo_ratio": 3.1,
            "attack_angle": 2.5
        }
        metrics = ProcessedMetrics(
            swing_id="test_swing",
            session_id="test_session",
            metrics=metric_data
        )
        
        assert metrics.metrics == metric_data


class TestRedisKey:
    """Test RedisKey model"""
    
    def test_redis_key_creation(self):
        """Test creating RedisKey"""
        redis_key = RedisKey(
            session_id="test_session",
            user_id="test_user",
            club_id="driver",
            data_type="imu"
        )
        
        assert redis_key.session_id == "test_session"
        assert redis_key.user_id == "test_user"
        assert redis_key.club_id == "driver"
        assert redis_key.data_type == "imu"
    
    def test_redis_key_to_key_method(self):
        """Test RedisKey.to_key() method"""
        redis_key = RedisKey(
            session_id="test_session",
            user_id="test_user",
            club_id="driver",
            data_type="imu"
        )
        
        expected_key = "session:test_session:user:test_user:club:driver:imu"
        assert redis_key.to_key() == expected_key
    
    def test_redis_key_different_data_types(self):
        """Test RedisKey with different data types"""
        imu_key = RedisKey(
            session_id="session1", user_id="user1",
            club_id="driver", data_type="imu"
        )
        events_key = RedisKey(
            session_id="session1", user_id="user1",
            club_id="driver", data_type="events"
        )
        
        assert imu_key.to_key() != events_key.to_key()
        assert "imu" in imu_key.to_key()
        assert "events" in events_key.to_key() 