"""
Tests for backend.session_manager module
"""
import pytest
from unittest.mock import Mock, patch
from backend.session_manager import SessionManager
from backend.models import SessionConfig, SwingEvent, IMUData, SwingData
from datetime import datetime


class TestSessionManager:
    """Test SessionManager class"""
    
    def test_session_manager_initialization(self, redis_manager_with_mock):
        """Test SessionManager initialization"""
        manager = SessionManager(redis_manager_with_mock)
        
        assert manager.redis_manager == redis_manager_with_mock
        assert manager.current_session is None
    
    def test_create_session_success(self, session_manager_with_mock):
        """Test successful session creation"""
        # Mock successful Redis storage
        session_manager_with_mock.redis_manager.store_session_config = Mock(return_value=True)
        
        result = session_manager_with_mock.create_session(
            user_id="test_user",
            club_id="driver",
            club_length=1.07,
            club_mass=0.205
        )
        
        assert result is not None
        assert isinstance(result, SessionConfig)
        assert result.user_id == "test_user"
        assert result.club_id == "driver"
        assert result.club_length == 1.07
        assert result.club_mass == 0.205
        assert result.impact_threshold == 30.0  # default
        assert session_manager_with_mock.current_session == result
        session_manager_with_mock.redis_manager.store_session_config.assert_called_once()
    
    def test_create_session_with_optional_fields(self, session_manager_with_mock):
        """Test session creation with optional fields"""
        session_manager_with_mock.redis_manager.store_session_config = Mock(return_value=True)
        face_normal = [1.0, 0.0, 0.0]
        
        result = session_manager_with_mock.create_session(
            user_id="test_user",
            club_id="driver",
            club_length=1.07,
            club_mass=0.205,
            face_normal_calibration=face_normal,
            impact_threshold=25.0
        )
        
        assert result.face_normal_calibration == face_normal
        assert result.impact_threshold == 25.0
    
    def test_create_session_redis_failure(self, session_manager_with_mock):
        """Test session creation when Redis storage fails"""
        session_manager_with_mock.redis_manager.store_session_config = Mock(return_value=False)
        
        with pytest.raises(Exception, match="Failed to create session"):
            session_manager_with_mock.create_session(
                user_id="test_user",
                club_id="driver",
                club_length=1.07,
                club_mass=0.205
            )
    
    def test_load_session_success(self, session_manager_with_mock, sample_session_config):
        """Test successful session loading"""
        session_manager_with_mock.redis_manager.get_session_config = Mock(return_value=sample_session_config)
        
        result = session_manager_with_mock.load_session("test_session_id")
        
        assert result == sample_session_config
        assert session_manager_with_mock.current_session == sample_session_config
    
    def test_load_session_not_found(self, session_manager_with_mock):
        """Test session loading when session not found"""
        session_manager_with_mock.redis_manager.get_session_config = Mock(return_value=None)
        
        result = session_manager_with_mock.load_session("nonexistent_session")
        
        assert result is None
        assert session_manager_with_mock.current_session is None
    
    def test_end_session_with_current_session(self, session_manager_with_mock, sample_session_config):
        """Test ending session when current session exists"""
        session_manager_with_mock.current_session = sample_session_config
        
        result = session_manager_with_mock.end_session()
        
        assert result is True
        assert session_manager_with_mock.current_session is None
    
    def test_end_session_no_current_session(self, session_manager_with_mock):
        """Test ending session when no current session"""
        result = session_manager_with_mock.end_session()
        
        assert result is False
    
    def test_clear_session_data_success(self, session_manager_with_mock):
        """Test successful session data clearing"""
        session_manager_with_mock.redis_manager.clear_session_data = Mock(return_value=True)
        
        result = session_manager_with_mock.clear_session_data("test_session_id")
        
        assert result is True
        session_manager_with_mock.redis_manager.clear_session_data.assert_called_once_with("test_session_id")
    
    def test_clear_session_data_failure(self, session_manager_with_mock):
        """Test session data clearing failure"""
        session_manager_with_mock.redis_manager.clear_session_data = Mock(return_value=False)
        
        result = session_manager_with_mock.clear_session_data("test_session_id")
        
        assert result is False
    
    def test_get_current_session_with_session(self, session_manager_with_mock, sample_session_config):
        """Test getting current session when session exists"""
        session_manager_with_mock.current_session = sample_session_config
        
        result = session_manager_with_mock.get_current_session()
        
        assert result == sample_session_config
    
    def test_get_current_session_no_session(self, session_manager_with_mock):
        """Test getting current session when no session exists"""
        result = session_manager_with_mock.get_current_session()
        
        assert result is None
    
    def test_log_swing_event_success(self, session_manager_with_mock, sample_session_config):
        """Test successful swing event logging"""
        session_manager_with_mock.current_session = sample_session_config
        session_manager_with_mock.redis_manager.store_swing_event = Mock(return_value=True)
        
        result = session_manager_with_mock.log_swing_event("impact", {"g_force": 35.0})
        
        assert result is not None
        assert isinstance(result, SwingEvent)
        assert result.event_type == "impact"
        assert result.data == {"g_force": 35.0}
        assert result.session_id == sample_session_config.session_id
        session_manager_with_mock.redis_manager.store_swing_event.assert_called_once()
    
    def test_log_swing_event_no_session(self, session_manager_with_mock):
        """Test swing event logging when no current session"""
        result = session_manager_with_mock.log_swing_event("impact")
        
        assert result is None
    
    def test_log_swing_event_redis_failure(self, session_manager_with_mock, sample_session_config):
        """Test swing event logging when Redis storage fails"""
        session_manager_with_mock.current_session = sample_session_config
        session_manager_with_mock.redis_manager.store_swing_event = Mock(return_value=False)
        
        result = session_manager_with_mock.log_swing_event("impact")
        
        assert result is None
    
    def test_get_session_summary_with_session(self, session_manager_with_mock, sample_session_config):
        """Test getting session summary when session exists"""
        session_manager_with_mock.current_session = sample_session_config
        session_manager_with_mock.redis_manager.get_imu_buffer = Mock(return_value=[Mock(), Mock()])  # 2 data points
        
        result = session_manager_with_mock.get_session_summary()
        
        assert result["session_id"] == sample_session_config.session_id
        assert result["user_id"] == sample_session_config.user_id
        assert result["club_id"] == sample_session_config.club_id
        assert result["club_length"] == sample_session_config.club_length
        assert result["club_mass"] == sample_session_config.club_mass
        assert result["impact_threshold"] == sample_session_config.impact_threshold
    
    def test_get_session_summary_no_session(self, session_manager_with_mock):
        """Test getting session summary when no session exists"""
        result = session_manager_with_mock.get_session_summary()
        
        assert result == {"error": "No active session"}
    
    def test_update_session_config_success(self, session_manager_with_mock, sample_session_config):
        """Test successful session config update"""
        session_manager_with_mock.current_session = sample_session_config
        session_manager_with_mock.redis_manager.store_session_config = Mock(return_value=True)
        
        result = session_manager_with_mock.update_session_config(
            impact_threshold=25.0,
            face_normal_calibration=[0.0, 1.0, 0.0]
        )
        
        assert result is True
        assert session_manager_with_mock.current_session.impact_threshold == 25.0
        assert session_manager_with_mock.current_session.face_normal_calibration == [0.0, 1.0, 0.0]
        session_manager_with_mock.redis_manager.store_session_config.assert_called_once()
    
    def test_update_session_config_no_session(self, session_manager_with_mock):
        """Test session config update when no session exists"""
        result = session_manager_with_mock.update_session_config(impact_threshold=25.0)
        
        assert result is False
    
    def test_update_session_config_invalid_field(self, session_manager_with_mock, sample_session_config):
        """Test session config update with invalid field"""
        session_manager_with_mock.current_session = sample_session_config
        
        result = session_manager_with_mock.update_session_config(invalid_field="value")
        
        assert result is True  # Should still succeed, just ignore invalid field
        assert not hasattr(session_manager_with_mock.current_session, 'invalid_field')
    
    def test_update_session_config_redis_failure(self, session_manager_with_mock, sample_session_config):
        """Test session config update when Redis storage fails"""
        session_manager_with_mock.current_session = sample_session_config
        session_manager_with_mock.redis_manager.store_session_config = Mock(return_value=False)
        
        result = session_manager_with_mock.update_session_config(impact_threshold=25.0)
        
        assert result is False
    
    def test_session_unique_ids(self, session_manager_with_mock):
        """Test that each session gets unique session_id"""
        session_manager_with_mock.redis_manager.store_session_config = Mock(return_value=True)
        
        session1 = session_manager_with_mock.create_session(
            user_id="test_user", club_id="driver", club_length=1.07, club_mass=0.205
        )
        session2 = session_manager_with_mock.create_session(
            user_id="test_user", club_id="driver", club_length=1.07, club_mass=0.205
        )
        
        assert session1.session_id != session2.session_id
    
    def test_swing_event_unique_ids(self, session_manager_with_mock, sample_session_config):
        """Test that each swing event gets unique swing_id"""
        session_manager_with_mock.current_session = sample_session_config
        session_manager_with_mock.redis_manager.store_swing_event = Mock(return_value=True)
        
        event1 = session_manager_with_mock.log_swing_event("impact")
        event2 = session_manager_with_mock.log_swing_event("impact")
        
        assert event1.swing_id != event2.swing_id
    
    def test_store_swing_data_success(self, session_manager_with_mock, sample_session_config):
        """Test successful swing data storage"""
        session_manager_with_mock.current_session = sample_session_config
        session_manager_with_mock.redis_manager.store_swing_data = Mock(return_value=True)
        
        # Create sample swing data
        sample_imu_data = IMUData(ax=1.0, ay=2.0, az=3.0, gx=4.0, gy=5.0, gz=6.0, mx=7.0, my=8.0, mz=9.0, qw=1.0, qx=0.0, qy=0.0, qz=0.0)
        swing_data = SwingData(
            session_id="",  # Will be set by session manager
            imu_data_points=[sample_imu_data],
            swing_start_time=datetime(2023, 1, 1, 12, 0, 0),
            swing_end_time=datetime(2023, 1, 1, 12, 0, 1),
            swing_duration=1.0,
            impact_g_force=30.0,
            swing_type="full_swing"
        )
        
        result = session_manager_with_mock.store_swing_data(swing_data)
        
        assert result is True
        # Check that session_id was set
        assert swing_data.session_id == sample_session_config.session_id
        session_manager_with_mock.redis_manager.store_swing_data.assert_called_once_with(swing_data, sample_session_config)
    
    def test_store_swing_data_no_session(self, session_manager_with_mock):
        """Test swing data storage without session"""
        # Create sample swing data
        sample_imu_data = IMUData(ax=1.0, ay=2.0, az=3.0, gx=4.0, gy=5.0, gz=6.0, mx=7.0, my=8.0, mz=9.0, qw=1.0, qx=0.0, qy=0.0, qz=0.0)
        swing_data = SwingData(
            session_id="test_session",
            imu_data_points=[sample_imu_data],
            swing_start_time=datetime(2023, 1, 1, 12, 0, 0),
            swing_end_time=datetime(2023, 1, 1, 12, 0, 1),
            swing_duration=1.0,
            impact_g_force=30.0,
            swing_type="full_swing"
        )
        
        result = session_manager_with_mock.store_swing_data(swing_data)
        
        assert result is False
    
    def test_store_swing_data_redis_failure(self, session_manager_with_mock, sample_session_config):
        """Test swing data storage when Redis fails"""
        session_manager_with_mock.current_session = sample_session_config
        session_manager_with_mock.redis_manager.store_swing_data = Mock(return_value=False)
        
        # Create sample swing data
        sample_imu_data = IMUData(ax=1.0, ay=2.0, az=3.0, gx=4.0, gy=5.0, gz=6.0, mx=7.0, my=8.0, mz=9.0, qw=1.0, qx=0.0, qy=0.0, qz=0.0)
        swing_data = SwingData(
            session_id="",
            imu_data_points=[sample_imu_data],
            swing_start_time=datetime(2023, 1, 1, 12, 0, 0),
            swing_end_time=datetime(2023, 1, 1, 12, 0, 1),
            swing_duration=1.0,
            impact_g_force=30.0,
            swing_type="full_swing"
        )
        
        result = session_manager_with_mock.store_swing_data(swing_data)
        
        assert result is False
    
    def test_get_swing_data_success(self, session_manager_with_mock, sample_session_config):
        """Test successful swing data retrieval"""
        session_manager_with_mock.current_session = sample_session_config
        session_manager_with_mock.redis_manager.get_swing_data = Mock(return_value=[Mock(), Mock()])  # 2 swings
        
        result = session_manager_with_mock.get_swing_data()
        
        assert len(result) == 2
        session_manager_with_mock.redis_manager.get_swing_data.assert_called_once_with(sample_session_config, None)
    
    def test_get_swing_data_with_count(self, session_manager_with_mock, sample_session_config):
        """Test swing data retrieval with specific count"""
        session_manager_with_mock.current_session = sample_session_config
        session_manager_with_mock.redis_manager.get_swing_data = Mock(return_value=[])
        
        session_manager_with_mock.get_swing_data(count=10)
        
        session_manager_with_mock.redis_manager.get_swing_data.assert_called_once_with(sample_session_config, 10)
    
    def test_get_swing_data_no_session(self, session_manager_with_mock):
        """Test swing data retrieval without session"""
        result = session_manager_with_mock.get_swing_data()
        
        assert result == []
    
    def test_get_swing_statistics_success(self, session_manager_with_mock, sample_session_config):
        """Test successful swing statistics retrieval"""
        session_manager_with_mock.current_session = sample_session_config
        
        # Mock swing data
        mock_swing1 = Mock()
        mock_swing1.swing_duration = 1.5
        mock_swing1.impact_g_force = 35.0
        mock_swing1.swing_type = "full_swing"
        
        mock_swing2 = Mock()
        mock_swing2.swing_duration = 1.2
        mock_swing2.impact_g_force = 32.0
        mock_swing2.swing_type = "chip"
        
        session_manager_with_mock.get_swing_data = Mock(return_value=[mock_swing1, mock_swing2])
        
        result = session_manager_with_mock.get_swing_statistics()
        
        assert result["swing_count"] == 2
        assert result["average_duration"] == 1.35  # (1.5 + 1.2) / 2
        assert result["average_impact_g"] == 33.5  # (35.0 + 32.0) / 2
        assert result["min_impact_g"] == 32.0
        assert result["max_impact_g"] == 35.0
        assert set(result["swing_types"]) == {"full_swing", "chip"}
    
    def test_get_swing_statistics_no_session(self, session_manager_with_mock):
        """Test swing statistics retrieval without session"""
        result = session_manager_with_mock.get_swing_statistics()
        
        assert result == {"error": "No active session"}
    
    def test_get_swing_statistics_no_swings(self, session_manager_with_mock, sample_session_config):
        """Test swing statistics retrieval with no swings"""
        session_manager_with_mock.current_session = sample_session_config
        session_manager_with_mock.get_swing_data = Mock(return_value=[])
        
        result = session_manager_with_mock.get_swing_statistics()
        
        assert result["swing_count"] == 0
        assert result["average_duration"] == 0
        assert result["average_impact_g"] == 0
    
    def test_get_imu_buffer_success(self, session_manager_with_mock, sample_session_config):
        """Test successful IMU buffer retrieval"""
        session_manager_with_mock.current_session = sample_session_config
        session_manager_with_mock.redis_manager.get_imu_buffer = Mock(return_value=[Mock(), Mock()])  # 2 data points
        
        result = session_manager_with_mock.get_imu_buffer()
        
        assert len(result) == 2
        session_manager_with_mock.redis_manager.get_imu_buffer.assert_called_once_with(sample_session_config, None)
    
    def test_get_imu_buffer_with_count(self, session_manager_with_mock, sample_session_config):
        """Test IMU buffer retrieval with specific count"""
        session_manager_with_mock.current_session = sample_session_config
        session_manager_with_mock.redis_manager.get_imu_buffer = Mock(return_value=[])
        
        session_manager_with_mock.get_imu_buffer(count=50)
        
        session_manager_with_mock.redis_manager.get_imu_buffer.assert_called_once_with(sample_session_config, 50)
    
    def test_get_imu_buffer_no_session(self, session_manager_with_mock):
        """Test IMU buffer retrieval without session"""
        result = session_manager_with_mock.get_imu_buffer()
        
        assert result == [] 