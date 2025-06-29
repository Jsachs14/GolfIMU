"""
Tests for backend.redis_manager module
"""
import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime
from backend.redis_manager import RedisManager
from backend.models import IMUData, SessionConfig, SwingEvent, RedisKey, SwingData


class TestRedisManager:
    """Test RedisManager class"""
    
    def test_redis_manager_initialization(self, mock_redis_client, monkeypatch):
        """Test RedisManager initialization"""
        manager = RedisManager()
        monkeypatch.setattr(manager, 'redis_client', mock_redis_client)
        
        assert manager.redis_client is not None
        assert hasattr(manager.redis_client, 'lpush')
        assert hasattr(manager.redis_client, 'ltrim')
        assert hasattr(manager.redis_client, 'lrange')
        assert hasattr(manager.redis_client, 'set')
        assert hasattr(manager.redis_client, 'get')
        assert hasattr(manager.redis_client, 'delete')
    
    def test_store_imu_data_success(self, redis_manager_with_mock, sample_imu_data, sample_session_config):
        """Test successful IMU data storage"""
        result = redis_manager_with_mock.store_imu_data(sample_imu_data, sample_session_config)
        
        assert result is True
        redis_manager_with_mock.redis_client.lpush.assert_called_once()
        redis_manager_with_mock.redis_client.ltrim.assert_called_once()
        
        # Check that lpush was called with correct key format
        call_args = redis_manager_with_mock.redis_client.lpush.call_args
        key = call_args[0][0]
        assert "session:" in key
        assert "user:" in key
        assert "club:" in key
        assert "imu" in key
        
        # Check that data was JSON serialized
        data_json = call_args[0][1]
        data_dict = json.loads(data_json)
        assert data_dict["ax"] == sample_imu_data.ax
        assert data_dict["ay"] == sample_imu_data.ay
        assert data_dict["az"] == sample_imu_data.az
    
    def test_store_imu_data_failure(self, redis_manager_with_mock, sample_imu_data, sample_session_config):
        """Test IMU data storage failure"""
        redis_manager_with_mock.redis_client.lpush.side_effect = Exception("Redis error")
        
        result = redis_manager_with_mock.store_imu_data(sample_imu_data, sample_session_config)
        
        assert result is False
    
    def test_get_imu_buffer_empty(self, redis_manager_with_mock, sample_session_config):
        """Test getting empty IMU buffer"""
        redis_manager_with_mock.redis_client.lrange.return_value = []
        
        result = redis_manager_with_mock.get_imu_buffer(sample_session_config)
        
        assert result == []
        redis_manager_with_mock.redis_client.lrange.assert_called_once()
    
    def test_get_imu_buffer_with_data(self, redis_manager_with_mock, sample_session_config):
        """Test getting IMU buffer with data"""
        # Mock Redis response with JSON data
        mock_data = [
            json.dumps({
                "ax": 1.0, "ay": 2.0, "az": 3.0,
                "gx": 4.0, "gy": 5.0, "gz": 6.0,
                "mx": 7.0, "my": 8.0, "mz": 9.0,
                "timestamp": "2023-01-01T12:00:00"
            })
        ]
        redis_manager_with_mock.redis_client.lrange.return_value = mock_data
        
        result = redis_manager_with_mock.get_imu_buffer(sample_session_config)
        
        assert len(result) == 1
        assert isinstance(result[0], IMUData)
        assert result[0].ax == 1.0
        assert result[0].ay == 2.0
        assert result[0].az == 3.0
    
    def test_get_imu_buffer_with_count(self, redis_manager_with_mock, sample_session_config):
        """Test getting IMU buffer with specific count"""
        redis_manager_with_mock.redis_client.lrange.return_value = []
        
        redis_manager_with_mock.get_imu_buffer(sample_session_config, count=50)
        
        # Check that lrange was called with count=50
        call_args = redis_manager_with_mock.redis_client.lrange.call_args
        assert call_args[0][2] == 49  # lrange uses 0-based indexing
    
    def test_get_imu_buffer_parse_error(self, redis_manager_with_mock, sample_session_config):
        """Test IMU buffer parsing error"""
        redis_manager_with_mock.redis_client.lrange.return_value = ["invalid-json"]
        
        result = redis_manager_with_mock.get_imu_buffer(sample_session_config)
        
        assert result == []
    
    def test_store_swing_event_success(self, redis_manager_with_mock, sample_swing_event):
        """Test successful swing event storage"""
        result = redis_manager_with_mock.store_swing_event(sample_swing_event)
        
        assert result is True
        redis_manager_with_mock.redis_client.lpush.assert_called_once()
        
        # Check that event was JSON serialized
        call_args = redis_manager_with_mock.redis_client.lpush.call_args
        event_json = call_args[0][1]
        event_dict = json.loads(event_json)
        assert event_dict["event_type"] == sample_swing_event.event_type
        assert event_dict["data"] == sample_swing_event.data
    
    def test_store_swing_event_failure(self, redis_manager_with_mock, sample_swing_event):
        """Test swing event storage failure"""
        redis_manager_with_mock.redis_client.lpush.side_effect = Exception("Redis error")
        
        result = redis_manager_with_mock.store_swing_event(sample_swing_event)
        
        assert result is False
    
    def test_store_session_config_success(self, redis_manager_with_mock, sample_session_config):
        """Test successful session config storage"""
        result = redis_manager_with_mock.store_session_config(sample_session_config)
        
        assert result is True
        redis_manager_with_mock.redis_client.set.assert_called_once()
        
        # Check that config was JSON serialized
        call_args = redis_manager_with_mock.redis_client.set.call_args
        config_json = call_args[0][1]
        config_dict = json.loads(config_json)
        assert config_dict["user_id"] == sample_session_config.user_id
        assert config_dict["club_id"] == sample_session_config.club_id
        assert config_dict["club_length"] == sample_session_config.club_length
    
    def test_store_session_config_failure(self, redis_manager_with_mock, sample_session_config):
        """Test session config storage failure"""
        redis_manager_with_mock.redis_client.set.side_effect = Exception("Redis error")
        
        result = redis_manager_with_mock.store_session_config(sample_session_config)
        
        assert result is False
    
    def test_get_session_config_success(self, redis_manager_with_mock, sample_session_config):
        """Test successful session config retrieval"""
        # Mock Redis response
        config_json = json.dumps({
            "session_id": sample_session_config.session_id,
            "user_id": sample_session_config.user_id,
            "club_id": sample_session_config.club_id,
            "club_length": sample_session_config.club_length,
            "club_mass": sample_session_config.club_mass,
            "face_normal_calibration": sample_session_config.face_normal_calibration,
            "impact_threshold": sample_session_config.impact_threshold,
            "session_start_time": sample_session_config.session_start_time.isoformat()
        })
        redis_manager_with_mock.redis_client.get.return_value = config_json
        
        result = redis_manager_with_mock.get_session_config(sample_session_config.session_id)
        
        assert result is not None
        assert isinstance(result, SessionConfig)
        assert result.user_id == sample_session_config.user_id
        assert result.club_id == sample_session_config.club_id
        assert result.club_length == sample_session_config.club_length
    
    def test_get_session_config_not_found(self, redis_manager_with_mock):
        """Test session config retrieval when not found"""
        redis_manager_with_mock.redis_client.get.return_value = None
        
        result = redis_manager_with_mock.get_session_config("nonexistent-session")
        
        assert result is None
    
    def test_get_session_config_parse_error(self, redis_manager_with_mock):
        """Test session config retrieval with parse error"""
        redis_manager_with_mock.redis_client.get.return_value = "invalid-json"
        
        result = redis_manager_with_mock.get_session_config("test-session")
        
        assert result is None
    
    def test_clear_session_data_success(self, redis_manager_with_mock, sample_session_config):
        """Test successful session data clearing"""
        # Mock get_session_config to return a valid config
        redis_manager_with_mock.get_session_config = Mock(return_value=sample_session_config)
        
        result = redis_manager_with_mock.clear_session_data(sample_session_config.session_id)
        
        assert result is True
        # Should call delete 3 times: for IMU data, events, and config
        assert redis_manager_with_mock.redis_client.delete.call_count == 3
    
    def test_clear_session_data_session_not_found(self, redis_manager_with_mock):
        """Test session data clearing when session not found"""
        redis_manager_with_mock.get_session_config = Mock(return_value=None)
        
        result = redis_manager_with_mock.clear_session_data("nonexistent-session")
        
        assert result is False
        redis_manager_with_mock.redis_client.delete.assert_not_called()
    
    def test_clear_session_data_failure(self, redis_manager_with_mock, sample_session_config):
        """Test session data clearing failure"""
        redis_manager_with_mock.get_session_config = Mock(return_value=sample_session_config)
        redis_manager_with_mock.redis_client.delete.side_effect = Exception("Redis error")
        
        result = redis_manager_with_mock.clear_session_data(sample_session_config.session_id)
        
        assert result is False
    
    def test_redis_key_generation(self, redis_manager_with_mock, sample_imu_data, sample_session_config):
        """Test Redis key generation for IMU data"""
        redis_manager_with_mock.store_imu_data(sample_imu_data, sample_session_config)
        
        # Check that the key was generated correctly
        call_args = redis_manager_with_mock.redis_client.lpush.call_args
        key = call_args[0][0]
        
        expected_key = f"session:{sample_session_config.session_id}:user:{sample_session_config.user_id}:club:{sample_session_config.club_id}:imu_buffer"
        assert key == expected_key
    
    def test_store_swing_data_success(self, redis_manager_with_mock, sample_session_config):
        """Test successful swing data storage"""
        # Create sample swing data
        sample_imu_data = IMUData(ax=1.0, ay=2.0, az=3.0, gx=4.0, gy=5.0, gz=6.0, mx=7.0, my=8.0, mz=9.0)
        swing_data = SwingData(
            session_id=sample_session_config.session_id,
            imu_data_points=[sample_imu_data],
            swing_start_time=datetime(2023, 1, 1, 12, 0, 0),
            swing_end_time=datetime(2023, 1, 1, 12, 0, 1),
            swing_duration=1.0,
            impact_g_force=30.0,
            swing_type="full_swing"
        )
        
        result = redis_manager_with_mock.store_swing_data(swing_data, sample_session_config)
        
        assert result is True
        redis_manager_with_mock.redis_client.lpush.assert_called_once()
        
        # Check that swing data was JSON serialized
        call_args = redis_manager_with_mock.redis_client.lpush.call_args
        swing_json = call_args[0][1]
        swing_dict = json.loads(swing_json)
        assert swing_dict["swing_id"] == swing_data.swing_id
        assert swing_dict["session_id"] == swing_data.session_id
        assert len(swing_dict["imu_data_points"]) == 1
        assert swing_dict["swing_duration"] == 1.0
        assert swing_dict["impact_g_force"] == 30.0
        assert swing_dict["swing_type"] == "full_swing"
    
    def test_store_swing_data_failure(self, redis_manager_with_mock, sample_session_config):
        """Test swing data storage failure"""
        redis_manager_with_mock.redis_client.lpush.side_effect = Exception("Redis error")
        
        sample_imu_data = IMUData(ax=1.0, ay=2.0, az=3.0, gx=4.0, gy=5.0, gz=6.0, mx=7.0, my=8.0, mz=9.0)
        swing_data = SwingData(
            session_id=sample_session_config.session_id,
            imu_data_points=[sample_imu_data],
            swing_start_time=datetime(2023, 1, 1, 12, 0, 0),
            swing_end_time=datetime(2023, 1, 1, 12, 0, 1),
            swing_duration=1.0,
            impact_g_force=30.0,
            swing_type="full_swing"
        )
        
        result = redis_manager_with_mock.store_swing_data(swing_data, sample_session_config)
        
        assert result is False
    
    def test_get_swing_data_success(self, redis_manager_with_mock, sample_session_config):
        """Test successful swing data retrieval"""
        # Mock Redis response with swing data
        mock_swing_data = {
            "swing_id": "test_swing",
            "session_id": sample_session_config.session_id,
            "imu_data_points": [
                {
                    "ax": 1.0, "ay": 2.0, "az": 3.0,
                    "gx": 4.0, "gy": 5.0, "gz": 6.0,
                    "mx": 7.0, "my": 8.0, "mz": 9.0,
                    "timestamp": "2023-01-01T12:00:00"
                }
            ],
            "swing_start_time": "2023-01-01T12:00:00",
            "swing_end_time": "2023-01-01T12:00:01",
            "swing_duration": 1.0,
            "impact_g_force": 30.0,
            "swing_type": "full_swing"
        }
        
        redis_manager_with_mock.redis_client.lrange.return_value = [json.dumps(mock_swing_data)]
        
        result = redis_manager_with_mock.get_swing_data(sample_session_config)
        
        assert len(result) == 1
        assert isinstance(result[0], SwingData)
        assert result[0].swing_id == "test_swing"
        assert result[0].session_id == sample_session_config.session_id
        assert len(result[0].imu_data_points) == 1
        assert result[0].swing_duration == 1.0
        assert result[0].impact_g_force == 30.0
        assert result[0].swing_type == "full_swing"
    
    def test_get_swing_data_empty(self, redis_manager_with_mock, sample_session_config):
        """Test swing data retrieval with empty data"""
        redis_manager_with_mock.redis_client.lrange.return_value = []
        
        result = redis_manager_with_mock.get_swing_data(sample_session_config)
        
        assert result == []
    
    def test_get_swing_data_with_count(self, redis_manager_with_mock, sample_session_config):
        """Test swing data retrieval with specific count"""
        redis_manager_with_mock.redis_client.lrange.return_value = []
        
        redis_manager_with_mock.get_swing_data(sample_session_config, count=50)
        
        # Check that lrange was called with count=50
        call_args = redis_manager_with_mock.redis_client.lrange.call_args
        assert call_args[0][2] == 49  # lrange uses 0-based indexing
    
    def test_get_swing_data_parse_error(self, redis_manager_with_mock, sample_session_config):
        """Test swing data retrieval with parse error"""
        redis_manager_with_mock.redis_client.lrange.return_value = ["invalid-json"]
        
        result = redis_manager_with_mock.get_swing_data(sample_session_config)
        
        assert result == []
    
    def test_get_swing_data_exception(self, redis_manager_with_mock, sample_session_config):
        """Test swing data retrieval with exception"""
        redis_manager_with_mock.redis_client.lrange.side_effect = Exception("Redis error")
        
        result = redis_manager_with_mock.get_swing_data(sample_session_config)
        
        assert result == []
    
    def test_get_session_swing_count_success(self, redis_manager_with_mock, sample_session_config):
        """Test successful swing count retrieval"""
        redis_manager_with_mock.redis_client.llen.return_value = 5
        
        result = redis_manager_with_mock.get_session_swing_count(sample_session_config)
        
        assert result == 5
        redis_manager_with_mock.redis_client.llen.assert_called_once()
    
    def test_get_session_swing_count_exception(self, redis_manager_with_mock, sample_session_config):
        """Test swing count retrieval with exception"""
        redis_manager_with_mock.redis_client.llen.side_effect = Exception("Redis error")
        
        result = redis_manager_with_mock.get_session_swing_count(sample_session_config)
        
        assert result == 0
    
    def test_get_imu_buffer_parse_error_handling(self, redis_manager_with_mock, sample_session_config):
        """Test IMU buffer retrieval with parse error handling"""
        # Mock Redis response with some invalid data
        mock_data = [
            json.dumps({
                "ax": 1.0, "ay": 2.0, "az": 3.0,
                "gx": 4.0, "gy": 5.0, "gz": 6.0,
                "mx": 7.0, "my": 8.0, "mz": 9.0,
                "timestamp": "2023-01-01T12:00:00"
            }),
            "invalid-json",  # This should be skipped
            json.dumps({
                "ax": 2.0, "ay": 3.0, "az": 4.0,
                "gx": 5.0, "gy": 6.0, "gz": 7.0,
                "mx": 8.0, "my": 9.0, "mz": 10.0,
                "timestamp": "2023-01-01T12:01:00"
            })
        ]
        redis_manager_with_mock.redis_client.lrange.return_value = mock_data
        
        result = redis_manager_with_mock.get_imu_buffer(sample_session_config)
        
        # Should return 2 valid data points, skipping the invalid one
        # Note: The implementation reverses the list, so the first item in result is the last in mock_data
        assert len(result) == 2
        assert result[0].ax == 2.0  # This is the last item in mock_data (after reversal)
        assert result[1].ax == 1.0  # This is the first item in mock_data (after reversal) 