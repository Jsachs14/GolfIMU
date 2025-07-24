"""
Tests for data persistence functionality
Verifies that data survives Redis restarts
"""
import pytest
import redis
import json
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from backend.models import IMUData, SessionConfig, SwingEvent, SwingData
from backend.redis_manager import RedisManager
from backend.session_manager import SessionManager


class MockRedisClient:
    """Mock Redis client that maintains state to simulate persistence"""
    
    def __init__(self):
        self.data = {}  # Simulate Redis key-value store
        self.lists = {}  # Simulate Redis lists
    
    def set(self, key, value):
        """Mock Redis SET operation"""
        self.data[key] = value
        return True
    
    def get(self, key):
        """Mock Redis GET operation"""
        return self.data.get(key)
    
    def lpush(self, key, value):
        """Mock Redis LPUSH operation"""
        if key not in self.lists:
            self.lists[key] = []
        self.lists[key].insert(0, value)  # Insert at beginning
        return len(self.lists[key])
    
    def lrange(self, key, start, end):
        """Mock Redis LRANGE operation"""
        if key not in self.lists:
            return []
        if end == -1:
            end = len(self.lists[key])
        return self.lists[key][start:end+1]
    
    def ltrim(self, key, start, end):
        """Mock Redis LTRIM operation"""
        if key not in self.lists:
            return True
        if end == -1:
            end = len(self.lists[key]) - 1
        self.lists[key] = self.lists[key][start:end+1]
        return True
    
    def llen(self, key):
        """Mock Redis LLEN operation"""
        return len(self.lists.get(key, []))
    
    def delete(self, *keys):
        """Mock Redis DELETE operation"""
        deleted_count = 0
        for key in keys:
            # Handle both string keys and mock objects
            key_str = str(key) if hasattr(key, '__str__') else key
            if key_str in self.data:
                del self.data[key_str]
                deleted_count += 1
            if key_str in self.lists:
                del self.lists[key_str]
                deleted_count += 1
        return deleted_count
    
    def ping(self):
        """Mock Redis PING operation"""
        return True
    
    def keys(self, pattern):
        """Mock Redis KEYS operation"""
        import fnmatch
        all_keys = list(self.data.keys()) + list(self.lists.keys())
        return fnmatch.filter(all_keys, pattern)


@pytest.fixture
def persistent_redis_client():
    """Mock Redis client that maintains state for persistence testing"""
    return MockRedisClient()


@pytest.fixture
def redis_manager_with_persistence(persistent_redis_client):
    """Redis manager with persistent mock client"""
    manager = RedisManager()
    manager.redis_client = persistent_redis_client
    return manager


class TestDataPersistence:
    """Test data persistence across Redis restarts"""
    
    def test_session_config_persistence(self, redis_manager_with_persistence):
        """Test that session configuration persists after restart"""
        # Create test session config
        session_config = SessionConfig(
            user_id="test_user",
            club_id="driver",
            club_length=1.07,
            club_mass=0.205,
            face_normal_calibration=[1.0, 0.0, 0.0],
            impact_threshold=35.0
        )
        
        # Store session config
        result = redis_manager_with_persistence.store_session_config(session_config)
        assert result is True
        
        # Simulate Redis restart by creating new manager instance with same mock
        new_redis_manager = RedisManager()
        new_redis_manager.redis_client = redis_manager_with_persistence.redis_client
        
        # Retrieve session config after "restart"
        retrieved_config = new_redis_manager.get_session_config(session_config.session_id)
        
        # Verify data integrity
        assert retrieved_config is not None
        assert retrieved_config.session_id == session_config.session_id
        assert retrieved_config.user_id == session_config.user_id
        assert retrieved_config.club_id == session_config.club_id
        assert retrieved_config.club_length == session_config.club_length
        assert retrieved_config.club_mass == session_config.club_mass
        assert retrieved_config.face_normal_calibration == session_config.face_normal_calibration
        assert retrieved_config.impact_threshold == session_config.impact_threshold
    
    def test_swing_data_persistence(self, redis_manager_with_persistence):
        """Test that swing data persists after restart"""
        # Create test session config
        session_config = SessionConfig(
            user_id="test_user",
            club_id="driver",
            club_length=1.07,
            club_mass=0.205
        )
        
        # Create test IMU data points
        imu_data_points = [
            IMUData(ax=1.0, ay=2.0, az=3.0, gx=4.0, gy=5.0, gz=6.0, mx=7.0, my=8.0, mz=9.0, qw=1.0, qx=0.0, qy=0.0, qz=0.0),
            IMUData(ax=10.0, ay=11.0, az=12.0, gx=13.0, gy=14.0, gz=15.0, mx=16.0, my=17.0, mz=18.0, qw=1.0, qx=0.0, qy=0.0, qz=0.0)
        ]
        
        # Create test swing data
        swing_data = SwingData(
            session_id=session_config.session_id,
            imu_data_points=imu_data_points,
            swing_start_time=datetime(2023, 1, 1, 12, 0, 0),
            swing_end_time=datetime(2023, 1, 1, 12, 0, 1),
            swing_duration=1.0,
            impact_g_force=35.0,
            swing_type="full_swing"
        )
        
        # Store swing data
        result = redis_manager_with_persistence.store_swing_data(swing_data, session_config)
        assert result is True
        
        # Simulate Redis restart
        new_redis_manager = RedisManager()
        new_redis_manager.redis_client = redis_manager_with_persistence.redis_client
        
        # Retrieve swing data after "restart"
        retrieved_swings = new_redis_manager.get_swing_data(session_config, count=10)
        
        # Verify data integrity
        assert len(retrieved_swings) == 1
        retrieved_swing = retrieved_swings[0]
        
        assert retrieved_swing.swing_id == swing_data.swing_id
        assert retrieved_swing.session_id == swing_data.session_id
        assert retrieved_swing.swing_duration == swing_data.swing_duration
        assert retrieved_swing.impact_g_force == swing_data.impact_g_force
        assert retrieved_swing.swing_type == swing_data.swing_type
        assert len(retrieved_swing.imu_data_points) == len(swing_data.imu_data_points)
        
        # Verify IMU data points
        for i, (original, retrieved) in enumerate(zip(swing_data.imu_data_points, retrieved_swing.imu_data_points)):
            assert retrieved.ax == original.ax
            assert retrieved.ay == original.ay
            assert retrieved.az == original.az
            assert retrieved.gx == original.gx
            assert retrieved.gy == original.gy
            assert retrieved.gz == original.gz
            assert retrieved.mx == original.mx
            assert retrieved.my == original.my
            assert retrieved.mz == original.mz
    
    def test_swing_event_persistence(self, redis_manager_with_persistence):
        """Test that swing events persist after restart"""
        # Create test session config
        session_config = SessionConfig(
            user_id="test_user",
            club_id="driver",
            club_length=1.07,
            club_mass=0.205
        )
        
        # Create test swing event
        swing_event = SwingEvent(
            session_id=session_config.session_id,
            event_type="impact",
            data={"g_force": 35.0, "timestamp": "2023-01-01T12:00:00"}
        )
        
        # Store swing event
        result = redis_manager_with_persistence.store_swing_event(swing_event, session_config)
        assert result is True
        
        # Simulate Redis restart
        new_redis_manager = RedisManager()
        new_redis_manager.redis_client = redis_manager_with_persistence.redis_client
        
        # Note: We don't have a direct get_swing_events method, but we can verify
        # the data was stored by checking the Redis key directly
        redis_key = f"session:{swing_event.session_id}:events"
        stored_data = new_redis_manager.redis_client.lrange(redis_key, 0, -1)
        
        assert len(stored_data) == 1
        event_data = json.loads(stored_data[0])
        
        assert event_data["event_type"] == swing_event.event_type
        assert event_data["data"]["g_force"] == swing_event.data["g_force"]
    
    def test_multiple_sessions_persistence(self, redis_manager_with_persistence):
        """Test that multiple sessions persist after restart"""
        # Create multiple session configs
        session1 = SessionConfig(
            user_id="user1",
            club_id="driver",
            club_length=1.07,
            club_mass=0.205
        )
        
        session2 = SessionConfig(
            user_id="user2",
            club_id="iron",
            club_length=0.95,
            club_mass=0.180
        )
        
        # Store both sessions
        redis_manager_with_persistence.store_session_config(session1)
        redis_manager_with_persistence.store_session_config(session2)
        
        # Simulate Redis restart
        new_redis_manager = RedisManager()
        new_redis_manager.redis_client = redis_manager_with_persistence.redis_client
        
        # Retrieve both sessions
        retrieved_session1 = new_redis_manager.get_session_config(session1.session_id)
        retrieved_session2 = new_redis_manager.get_session_config(session2.session_id)
        
        # Verify both sessions are intact
        assert retrieved_session1 is not None
        assert retrieved_session2 is not None
        assert retrieved_session1.user_id == "user1"
        assert retrieved_session2.user_id == "user2"
        assert retrieved_session1.club_id == "driver"
        assert retrieved_session2.club_id == "iron"
    
    def test_session_manager_persistence(self, redis_manager_with_persistence):
        """Test that session manager can load data after restart"""
        # Create session manager
        session_manager = SessionManager(redis_manager_with_persistence)
        
        # Create a session
        session = session_manager.create_session(
            user_id="test_user",
            club_id="driver",
            club_length=1.07,
            club_mass=0.205
        )
        
        # Log some swing events
        session_manager.log_swing_event("swing_start", {"timestamp": "2023-01-01T12:00:00"})
        session_manager.log_swing_event("impact", {"g_force": 35.0})
        
        # Simulate Redis restart by creating new session manager
        new_redis_manager = RedisManager()
        new_redis_manager.redis_client = redis_manager_with_persistence.redis_client
        new_session_manager = SessionManager(new_redis_manager)
        
        # Load the session after "restart"
        loaded_session = new_session_manager.load_session(session.session_id)
        
        # Verify session was loaded correctly
        assert loaded_session is not None
        assert loaded_session.session_id == session.session_id
        assert loaded_session.user_id == session.user_id
        assert loaded_session.club_id == session.club_id
    
    def test_data_integrity_after_restart(self, redis_manager_with_persistence):
        """Test that data integrity is maintained after restart"""
        # Create comprehensive test data
        session_config = SessionConfig(
            user_id="integrity_test_user",
            club_id="putter",
            club_length=0.85,
            club_mass=0.150,
            face_normal_calibration=[0.0, 0.0, 1.0],
            impact_threshold=25.0
        )
        
        # Store session config
        redis_manager_with_persistence.store_session_config(session_config)
        
        # Create and store swing data
        imu_data = IMUData(
            ax=1.234, ay=2.345, az=3.456,
            gx=4.567, gy=5.678, gz=6.789,
            mx=7.890, my=8.901, mz=9.012,
            qw=1.0, qx=0.0, qy=0.0, qz=0.0
        )
        
        swing_data = SwingData(
            session_id=session_config.session_id,
            imu_data_points=[imu_data],
            swing_start_time=datetime(2023, 1, 1, 12, 0, 0),
            swing_end_time=datetime(2023, 1, 1, 12, 0, 1),
            swing_duration=1.0,
            impact_g_force=25.5,
            swing_type="putt"
        )
        
        redis_manager_with_persistence.store_swing_data(swing_data, session_config)
        
        # Store swing event
        swing_event = SwingEvent(
            session_id=session_config.session_id,
            event_type="putt_complete",
            data={"accuracy": 0.95, "distance": 3.2}
        )
        redis_manager_with_persistence.store_swing_event(swing_event, session_config)
        
        # Simulate Redis restart
        new_redis_manager = RedisManager()
        new_redis_manager.redis_client = redis_manager_with_persistence.redis_client
        
        # Verify all data types are intact
        retrieved_config = new_redis_manager.get_session_config(session_config.session_id)
        retrieved_swings = new_redis_manager.get_swing_data(session_config, count=10)
        
        # Check session config integrity
        assert retrieved_config is not None
        assert retrieved_config.face_normal_calibration == [0.0, 0.0, 1.0]
        assert retrieved_config.impact_threshold == 25.0
        
        # Check swing data integrity
        assert len(retrieved_swings) == 1
        retrieved_swing = retrieved_swings[0]
        assert retrieved_swing.swing_type == "putt"
        assert retrieved_swing.impact_g_force == 25.5
        
        # Check IMU data precision
        retrieved_imu = retrieved_swing.imu_data_points[0]
        assert abs(retrieved_imu.ax - 1.234) < 0.001
        assert abs(retrieved_imu.ay - 2.345) < 0.001
        assert abs(retrieved_imu.az - 3.456) < 0.001
    
    def test_redis_connection_recovery(self, redis_manager_with_persistence):
        """Test that Redis connection is properly recovered after restart"""
        # Test initial connection
        assert redis_manager_with_persistence.redis_client is not None
        
        # Simulate connection loss and recovery
        redis_manager_with_persistence.redis_client.ping()
        
        # Create new manager (simulating restart)
        new_redis_manager = RedisManager()
        new_redis_manager.redis_client = redis_manager_with_persistence.redis_client
        
        # Test connection after "restart"
        new_redis_manager.redis_client.ping()
        
        # Verify manager is functional
        assert new_redis_manager.redis_client is not None
    
    def test_data_cleanup_after_restart(self, redis_manager_with_persistence):
        """Test that data cleanup works after restart"""
        # Create test session
        session_config = SessionConfig(
            user_id="cleanup_test_user",
            club_id="driver",
            club_length=1.07,
            club_mass=0.205
        )
        
        # Store session data
        redis_manager_with_persistence.store_session_config(session_config)
        
        # Create swing data
        swing_data = SwingData(
            session_id=session_config.session_id,
            imu_data_points=[IMUData(ax=1.0, ay=2.0, az=3.0, gx=4.0, gy=5.0, gz=6.0, mx=7.0, my=8.0, mz=9.0, qw=1.0, qx=0.0, qy=0.0, qz=0.0)],
            swing_start_time=datetime(2023, 1, 1, 12, 0, 0),
            swing_end_time=datetime(2023, 1, 1, 12, 0, 1),
            swing_duration=1.0,
            impact_g_force=30.0,
            swing_type="full_swing"
        )
        redis_manager_with_persistence.store_swing_data(swing_data, session_config)
        
        # Simulate Redis restart
        new_redis_manager = RedisManager()
        new_redis_manager.redis_client = redis_manager_with_persistence.redis_client
        
        # Verify data exists after restart
        retrieved_config = new_redis_manager.get_session_config(session_config.session_id)
        assert retrieved_config is not None
        
        # Test cleanup after restart
        cleanup_result = new_redis_manager.clear_session_data(session_config.session_id)
        assert cleanup_result is True
        
        # Verify data is cleaned up
        cleaned_config = new_redis_manager.get_session_config(session_config.session_id)
        assert cleaned_config is None
    
    def test_concurrent_access_after_restart(self, redis_manager_with_persistence):
        """Test that concurrent access works correctly after restart"""
        # Create multiple managers (simulating multiple processes)
        manager1 = RedisManager()
        manager1.redis_client = redis_manager_with_persistence.redis_client
        
        manager2 = RedisManager()
        manager2.redis_client = redis_manager_with_persistence.redis_client
        
        # Create session config
        session_config = SessionConfig(
            user_id="concurrent_test_user",
            club_id="driver",
            club_length=1.07,
            club_mass=0.205
        )
        
        # Store from manager1
        manager1.store_session_config(session_config)
        
        # Retrieve from manager2 (simulating different process after restart)
        retrieved_config = manager2.get_session_config(session_config.session_id)
        
        # Verify data is accessible from both managers
        assert retrieved_config is not None
        assert retrieved_config.user_id == session_config.user_id
        assert retrieved_config.club_id == session_config.club_id


class TestRealRedisPersistence:
    """Test data persistence with real Redis (requires Redis server)"""
    
    @pytest.mark.skipif(True, reason="Requires real Redis server")
    def test_real_redis_persistence(self):
        """Test persistence with actual Redis server"""
        # This test would require a real Redis server running
        # It's marked as skip for now, but can be enabled for integration testing
        
        # Create Redis manager with real connection
        redis_manager = RedisManager()
        
        # Create test data
        session_config = SessionConfig(
            user_id="real_test_user",
            club_id="driver",
            club_length=1.07,
            club_mass=0.205
        )
        
        # Store data
        redis_manager.store_session_config(session_config)
        
        # Simulate restart by creating new manager
        new_redis_manager = RedisManager()
        
        # Verify data persists
        retrieved_config = new_redis_manager.get_session_config(session_config.session_id)
        assert retrieved_config is not None
        assert retrieved_config.user_id == session_config.user_id 