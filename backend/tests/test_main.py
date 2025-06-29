"""
Tests for backend.main module
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.main import GolfIMUBackend
from backend.models import IMUData, SessionConfig
from datetime import datetime


class TestGolfIMUBackend:
    """Test GolfIMUBackend class"""
    
    def test_backend_initialization(self):
        """Test GolfIMUBackend initialization"""
        backend = GolfIMUBackend()
        
        assert backend.redis_manager is not None
        assert backend.serial_manager is not None
        assert backend.session_manager is not None
        assert backend.running is False
    
    def test_start_session_success(self):
        """Test successful session start"""
        backend = GolfIMUBackend()
        backend.session_manager.create_session = Mock(return_value=Mock())
        
        result = backend.start_session(
            user_id="test_user",
            club_id="driver",
            club_length=1.07,
            club_mass=0.205
        )
        
        assert result is True
        backend.session_manager.create_session.assert_called_once()
    
    def test_start_session_failure(self):
        """Test session start failure"""
        backend = GolfIMUBackend()
        backend.session_manager.create_session = Mock(side_effect=Exception("Session error"))
        
        result = backend.start_session(
            user_id="test_user",
            club_id="driver",
            club_length=1.07,
            club_mass=0.205
        )
        
        assert result is False
    
    def test_connect_arduino_success(self):
        """Test successful Arduino connection"""
        backend = GolfIMUBackend()
        backend.serial_manager.connect = Mock(return_value=True)
        
        result = backend.connect_arduino("/dev/tty.test")
        
        assert result is True
        backend.serial_manager.connect.assert_called_once_with("/dev/tty.test")
    
    def test_connect_arduino_failure(self):
        """Test Arduino connection failure"""
        backend = GolfIMUBackend()
        backend.serial_manager.connect = Mock(return_value=False)
        
        result = backend.connect_arduino("/dev/tty.test")
        
        assert result is False
    
    def test_connect_arduino_auto_detect(self):
        """Test Arduino connection with auto-detection"""
        backend = GolfIMUBackend()
        backend.serial_manager.connect = Mock(return_value=True)
        
        result = backend.connect_arduino()
        
        assert result is True
        backend.serial_manager.connect.assert_called_once_with(None)
    
    def test_disconnect_arduino(self):
        """Test Arduino disconnection"""
        backend = GolfIMUBackend()
        backend.serial_manager.disconnect = Mock()
        
        backend.disconnect_arduino()
        
        backend.serial_manager.disconnect.assert_called_once()
    
    def test_start_data_collection_no_session(self):
        """Test starting data collection without session"""
        backend = GolfIMUBackend()
        backend.session_manager.get_current_session = Mock(return_value=None)
        
        backend.start_data_collection()
        
        # Should not start collection, no error should be raised
        assert backend.running is False
    
    def test_start_data_collection_no_arduino(self):
        """Test starting data collection without Arduino connection"""
        backend = GolfIMUBackend()
        backend.session_manager.get_current_session = Mock(return_value=Mock())
        backend.serial_manager.is_connected = False
        
        backend.start_data_collection()
        
        assert backend.running is False
    
    @patch('backend.main.time.sleep')
    def test_start_data_collection_success(self, mock_sleep):
        """Test successful data collection start"""
        backend = GolfIMUBackend()
        
        # Mock session and Arduino connection
        mock_session = Mock()
        backend.session_manager.get_current_session = Mock(return_value=mock_session)
        backend.serial_manager.is_connected = True
        
        # Mock IMU data stream
        mock_imu_data = IMUData(ax=1.0, ay=2.0, az=3.0, gx=4.0, gy=5.0, gz=6.0, mx=7.0, my=8.0, mz=9.0)
        backend.serial_manager.imu_data_stream = Mock(return_value=[mock_imu_data])
        
        # Mock Redis storage
        backend.redis_manager.store_imu_data = Mock(return_value=True)
        
        # Start collection (will process one data point then stop)
        backend.start_data_collection()
        
        # Verify data was stored
        backend.redis_manager.store_imu_data.assert_called_once()
        assert backend.running is False  # Should stop after processing
    
    def test_detect_impact_above_threshold(self):
        """Test impact detection above threshold"""
        backend = GolfIMUBackend()
        
        # Mock session with impact threshold
        mock_session = Mock()
        mock_session.impact_threshold = 30.0
        backend.session_manager.get_current_session = Mock(return_value=mock_session)
        backend.session_manager.log_swing_event = Mock(return_value=Mock())
        
        # Create IMU data with high acceleration (above 30g threshold)
        imu_data = IMUData(
            ax=300.0,  # High acceleration in m/s² (about 30g)
            ay=0.0, az=0.0,
            gx=0.0, gy=0.0, gz=0.0,
            mx=0.0, my=0.0, mz=0.0
        )
        
        backend._detect_impact(imu_data)
        
        # Should log impact event
        backend.session_manager.log_swing_event.assert_called_once()
        call_args = backend.session_manager.log_swing_event.call_args
        assert call_args[0][0] == "impact"
        assert "g_force" in call_args[0][1]
    
    def test_detect_impact_below_threshold(self):
        """Test impact detection below threshold"""
        backend = GolfIMUBackend()
        
        # Mock session with impact threshold
        mock_session = Mock()
        mock_session.impact_threshold = 30.0
        backend.session_manager.get_current_session = Mock(return_value=mock_session)
        backend.session_manager.log_swing_event = Mock(return_value=Mock())
        
        # Create IMU data with low acceleration (below 30g threshold)
        imu_data = IMUData(
            ax=10.0,  # Low acceleration in m/s² (about 1g)
            ay=0.0, az=0.0,
            gx=0.0, gy=0.0, gz=0.0,
            mx=0.0, my=0.0, mz=0.0
        )
        
        backend._detect_impact(imu_data)
        
        # Should not log impact event
        backend.session_manager.log_swing_event.assert_not_called()
    
    def test_detect_impact_no_session(self):
        """Test impact detection without session"""
        backend = GolfIMUBackend()
        backend.session_manager.get_current_session = Mock(return_value=None)
        backend.session_manager.log_swing_event = Mock()
        
        imu_data = IMUData(ax=100.0, ay=0.0, az=0.0, gx=0.0, gy=0.0, gz=0.0, mx=0.0, my=0.0, mz=0.0)
        
        backend._detect_impact(imu_data)
        
        # Should not log impact event
        backend.session_manager.log_swing_event.assert_not_called()
    
    def test_stop(self):
        """Test backend stop"""
        backend = GolfIMUBackend()
        backend.running = True
        backend.serial_manager.disconnect = Mock()
        
        backend.stop()
        
        assert backend.running is False
        backend.serial_manager.disconnect.assert_called_once()
    
    def test_get_status(self):
        """Test getting backend status"""
        backend = GolfIMUBackend()
        
        # Mock connection status
        backend.serial_manager.get_connection_status = Mock(return_value=(True, "/dev/tty.test"))
        
        # Mock current session
        mock_session = Mock()
        mock_session.session_id = "test_session"
        mock_session.user_id = "test_user"
        mock_session.club_id = "driver"
        backend.session_manager.get_current_session = Mock(return_value=mock_session)
        
        # Mock running state
        backend.running = True
        
        status = backend.get_status()
        
        assert status["arduino_connected"] is True
        assert status["arduino_port"] == "/dev/tty.test"
        assert status["session_active"] is True
        assert status["session_id"] == "test_session"
        assert status["user_id"] == "test_user"
        assert status["club_id"] == "driver"
        assert status["data_collection_running"] is True
    
    def test_get_status_no_session(self):
        """Test getting status without session"""
        backend = GolfIMUBackend()
        backend.serial_manager.get_connection_status = Mock(return_value=(False, None))
        backend.session_manager.get_current_session = Mock(return_value=None)
        backend.running = False
        
        status = backend.get_status()
        
        assert status["arduino_connected"] is False
        assert status["arduino_port"] is None
        assert status["session_active"] is False
        assert status["session_id"] is None
        assert status["user_id"] is None
        assert status["club_id"] is None
        assert status["data_collection_running"] is False
    
    def test_get_session_summary(self):
        """Test getting session summary"""
        backend = GolfIMUBackend()
        backend.session_manager.get_session_summary = Mock(return_value={"test": "summary"})
        
        summary = backend.get_session_summary()
        
        assert summary == {"test": "summary"}
        backend.session_manager.get_session_summary.assert_called_once()
    
    def test_signal_handler(self):
        """Test signal handler"""
        backend = GolfIMUBackend()
        backend.stop = Mock()
        
        # Simulate signal handler call - should raise SystemExit
        with pytest.raises(SystemExit):
            backend._signal_handler(1, None)
        
        backend.stop.assert_called_once()
    
    def test_g_force_calculation(self):
        """Test g-force calculation in impact detection"""
        backend = GolfIMUBackend()
        
        # Mock session
        mock_session = Mock()
        mock_session.impact_threshold = 30.0
        backend.session_manager.get_current_session = Mock(return_value=mock_session)
        backend.session_manager.log_swing_event = Mock(return_value=Mock())
        
        # Test with acceleration magnitude of 294.3 m/s² (30g)
        imu_data = IMUData(
            ax=294.3, ay=0.0, az=0.0,
            gx=0.0, gy=0.0, gz=0.0,
            mx=0.0, my=0.0, mz=0.0
        )
        
        backend._detect_impact(imu_data)
        
        # Should log impact event
        backend.session_manager.log_swing_event.assert_called_once()
        call_args = backend.session_manager.log_swing_event.call_args
        g_force = call_args[0][1]["g_force"]
        assert abs(g_force - 30.0) < 0.1  # Should be approximately 30g
    
    def test_data_collection_interruption(self):
        """Test data collection interruption"""
        backend = GolfIMUBackend()
        
        # Mock session and Arduino connection
        mock_session = Mock()
        backend.session_manager.get_current_session = Mock(return_value=mock_session)
        backend.serial_manager.is_connected = True
        
        # Mock IMU data stream that raises KeyboardInterrupt
        backend.serial_manager.imu_data_stream = Mock(side_effect=KeyboardInterrupt())
        
        # Should handle interruption gracefully
        backend.start_data_collection()
        
        assert backend.running is False
    
    def test_data_collection_exception(self):
        """Test data collection with exception"""
        backend = GolfIMUBackend()
        
        # Mock session and Arduino connection
        mock_session = Mock()
        backend.session_manager.get_current_session = Mock(return_value=mock_session)
        backend.serial_manager.is_connected = True
        
        # Mock IMU data stream that raises exception
        backend.serial_manager.imu_data_stream = Mock(side_effect=Exception("Data collection error"))
        
        # Should handle exception gracefully
        backend.start_data_collection()
        
        assert backend.running is False
    
    def test_send_session_config_to_arduino_success(self):
        """Test successful session config sending to Arduino"""
        backend = GolfIMUBackend()
        
        # Mock session and Arduino connection
        mock_session = Mock()
        backend.session_manager.get_current_session = Mock(return_value=mock_session)
        backend.serial_manager.is_connected = True
        backend.serial_manager.send_session_config = Mock(return_value=True)
        
        result = backend.send_session_config_to_arduino()
        
        assert result is True
        backend.serial_manager.send_session_config.assert_called_once_with(mock_session)
    
    def test_send_session_config_to_arduino_no_session(self):
        """Test session config sending without session"""
        backend = GolfIMUBackend()
        backend.session_manager.get_current_session = Mock(return_value=None)
        
        result = backend.send_session_config_to_arduino()
        
        assert result is False
    
    def test_send_session_config_to_arduino_no_arduino(self):
        """Test session config sending without Arduino connection"""
        backend = GolfIMUBackend()
        mock_session = Mock()
        backend.session_manager.get_current_session = Mock(return_value=mock_session)
        backend.serial_manager.is_connected = False
        
        result = backend.send_session_config_to_arduino()
        
        assert result is False
    
    def test_start_swing_monitoring_success(self):
        """Test successful swing monitoring start"""
        backend = GolfIMUBackend()
        backend.serial_manager.is_connected = True
        backend.serial_manager.start_swing_monitoring = Mock(return_value=True)
        
        result = backend.start_swing_monitoring()
        
        assert result is True
        backend.serial_manager.start_swing_monitoring.assert_called_once()
    
    def test_start_swing_monitoring_no_arduino(self):
        """Test swing monitoring start without Arduino connection"""
        backend = GolfIMUBackend()
        backend.serial_manager.is_connected = False
        
        result = backend.start_swing_monitoring()
        
        assert result is False
    
    def test_stop_swing_monitoring_success(self):
        """Test successful swing monitoring stop"""
        backend = GolfIMUBackend()
        backend.serial_manager.is_connected = True
        backend.serial_manager.stop_swing_monitoring = Mock(return_value=True)
        
        result = backend.stop_swing_monitoring()
        
        assert result is True
        backend.serial_manager.stop_swing_monitoring.assert_called_once()
    
    def test_stop_swing_monitoring_no_arduino(self):
        """Test swing monitoring stop without Arduino connection"""
        backend = GolfIMUBackend()
        backend.serial_manager.is_connected = False
        
        result = backend.stop_swing_monitoring()
        
        assert result is False
    
    def test_wait_for_swing_data_success(self):
        """Test successful swing data waiting"""
        backend = GolfIMUBackend()
        
        # Mock session and Arduino connection
        mock_session = Mock()
        backend.session_manager.get_current_session = Mock(return_value=mock_session)
        backend.serial_manager.is_connected = True
        
        # Mock swing data with proper attributes
        mock_swing_data = Mock()
        mock_swing_data.swing_id = "test_swing"
        mock_swing_data.swing_duration = 1.5  # Set as float for formatting
        mock_swing_data.impact_g_force = 30.0  # Set as float for formatting
        mock_swing_data.imu_data_points = [Mock(), Mock()]  # Set length for formatting
        backend.serial_manager.wait_for_swing_data = Mock(return_value=mock_swing_data)
        backend.session_manager.store_swing_data = Mock(return_value=True)
        
        result = backend.wait_for_swing_data()
        
        assert result == mock_swing_data
        backend.session_manager.store_swing_data.assert_called_once_with(mock_swing_data)
    
    def test_wait_for_swing_data_no_session(self):
        """Test swing data waiting without session"""
        backend = GolfIMUBackend()
        backend.session_manager.get_current_session = Mock(return_value=None)
        
        result = backend.wait_for_swing_data()
        
        assert result is None
    
    def test_wait_for_swing_data_no_arduino(self):
        """Test swing data waiting without Arduino connection"""
        backend = GolfIMUBackend()
        mock_session = Mock()
        backend.session_manager.get_current_session = Mock(return_value=mock_session)
        backend.serial_manager.is_connected = False
        
        result = backend.wait_for_swing_data()
        
        assert result is None
    
    def test_wait_for_swing_data_no_data(self):
        """Test swing data waiting when no data received"""
        backend = GolfIMUBackend()
        mock_session = Mock()
        backend.session_manager.get_current_session = Mock(return_value=mock_session)
        backend.serial_manager.is_connected = True
        backend.serial_manager.wait_for_swing_data = Mock(return_value=None)
        
        result = backend.wait_for_swing_data()
        
        assert result is None
    
    def test_wait_for_swing_data_storage_failure(self):
        """Test swing data waiting when storage fails"""
        backend = GolfIMUBackend()
        mock_session = Mock()
        backend.session_manager.get_current_session = Mock(return_value=mock_session)
        backend.serial_manager.is_connected = True
        mock_swing_data = Mock()
        backend.serial_manager.wait_for_swing_data = Mock(return_value=mock_swing_data)
        backend.session_manager.store_swing_data = Mock(return_value=False)
        
        result = backend.wait_for_swing_data()
        
        assert result is None
    
    @patch('backend.main.time.sleep')
    def test_start_continuous_monitoring_success(self, mock_sleep):
        """Test successful continuous monitoring start"""
        backend = GolfIMUBackend()
        
        # Mock session and Arduino connection
        mock_session = Mock()
        backend.session_manager.get_current_session = Mock(return_value=mock_session)
        backend.serial_manager.is_connected = True
        
        # Mock successful operations
        backend.send_session_config_to_arduino = Mock(return_value=True)
        backend.start_swing_monitoring = Mock(return_value=True)
        
        # Mock wait_for_swing_data to return None and then stop the loop
        call_count = 0
        def mock_wait_for_swing_data():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return None  # First call returns None
            else:
                backend.running = False  # Second call stops the loop
                return None
        
        backend.wait_for_swing_data = Mock(side_effect=mock_wait_for_swing_data)
        
        backend.start_continuous_monitoring()
        
        backend.send_session_config_to_arduino.assert_called_once()
        backend.start_swing_monitoring.assert_called_once()
        assert backend.running is False  # Should be False after the loop ends
    
    def test_start_continuous_monitoring_no_session(self):
        """Test continuous monitoring without session"""
        backend = GolfIMUBackend()
        backend.session_manager.get_current_session = Mock(return_value=None)
        
        backend.start_continuous_monitoring()
        
        # Should return early without starting monitoring
        assert backend.running is False
    
    def test_start_continuous_monitoring_no_arduino(self):
        """Test continuous monitoring without Arduino connection"""
        backend = GolfIMUBackend()
        mock_session = Mock()
        backend.session_manager.get_current_session = Mock(return_value=mock_session)
        backend.serial_manager.is_connected = False
        
        backend.start_continuous_monitoring()
        
        # Should return early without starting monitoring
        assert backend.running is False
    
    def test_start_continuous_monitoring_config_failure(self):
        """Test continuous monitoring when config sending fails"""
        backend = GolfIMUBackend()
        mock_session = Mock()
        backend.session_manager.get_current_session = Mock(return_value=mock_session)
        backend.serial_manager.is_connected = True
        backend.send_session_config_to_arduino = Mock(return_value=False)
        
        backend.start_continuous_monitoring()
        
        # Should return early without starting monitoring
        assert backend.running is False
    
    def test_start_continuous_monitoring_monitoring_failure(self):
        """Test continuous monitoring when monitoring start fails"""
        backend = GolfIMUBackend()
        mock_session = Mock()
        backend.session_manager.get_current_session = Mock(return_value=mock_session)
        backend.serial_manager.is_connected = True
        backend.send_session_config_to_arduino = Mock(return_value=True)
        backend.start_swing_monitoring = Mock(return_value=False)
        
        backend.start_continuous_monitoring()
        
        # Should return early without starting monitoring
        assert backend.running is False
    
    def test_process_swing_data(self):
        """Test swing data processing"""
        backend = GolfIMUBackend()
        backend.session_manager.log_swing_event = Mock(return_value=Mock())
        
        # Create mock swing data
        mock_swing_data = Mock()
        mock_swing_data.swing_id = "test_swing"
        mock_swing_data.swing_duration = 1.5
        mock_swing_data.impact_g_force = 35.0
        mock_swing_data.imu_data_points = [Mock(), Mock(), Mock()]  # 3 data points
        
        backend._process_swing_data(mock_swing_data)
        
        # Should log swing event
        backend.session_manager.log_swing_event.assert_called_once_with("swing_completed", {
            "swing_id": "test_swing",
            "duration": 1.5,
            "impact_g_force": 35.0,
            "data_points": 3
        })
    
    def test_get_swing_statistics(self):
        """Test getting swing statistics"""
        backend = GolfIMUBackend()
        backend.session_manager.get_swing_statistics = Mock(return_value={"test": "stats"})
        
        result = backend.get_swing_statistics()
        
        assert result == {"test": "stats"}
        backend.session_manager.get_swing_statistics.assert_called_once()
    
    def test_get_recent_swings(self):
        """Test getting recent swings"""
        backend = GolfIMUBackend()
        
        # Mock swing data
        mock_swing1 = Mock()
        mock_swing1.swing_id = "swing1"
        mock_swing1.swing_duration = 1.5
        mock_swing1.impact_g_force = 35.0
        mock_swing1.swing_type = "full_swing"
        mock_swing1.imu_data_points = [Mock(), Mock()]
        mock_swing1.swing_start_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_swing1.swing_end_time = datetime(2023, 1, 1, 12, 0, 1)
        
        mock_swing2 = Mock()
        mock_swing2.swing_id = "swing2"
        mock_swing2.swing_duration = 1.2
        mock_swing2.impact_g_force = 32.0
        mock_swing2.swing_type = "chip"
        mock_swing2.imu_data_points = [Mock()]
        mock_swing2.swing_start_time = datetime(2023, 1, 1, 12, 1, 0)
        mock_swing2.swing_end_time = datetime(2023, 1, 1, 12, 1, 1)
        
        backend.session_manager.get_swing_data = Mock(return_value=[mock_swing1, mock_swing2])
        
        result = backend.get_recent_swings(count=2)
        
        assert len(result) == 2
        assert result[0]["swing_id"] == "swing1"
        assert result[0]["duration"] == 1.5
        assert result[0]["impact_g_force"] == 35.0
        assert result[0]["swing_type"] == "full_swing"
        assert result[0]["data_points"] == 2
        assert result[1]["swing_id"] == "swing2"
        assert result[1]["duration"] == 1.2
        assert result[1]["impact_g_force"] == 32.0
        assert result[1]["swing_type"] == "chip"
        assert result[1]["data_points"] == 1
        
        backend.session_manager.get_swing_data.assert_called_once_with(count=2)
    
    def test_get_recent_swings_default_count(self):
        """Test getting recent swings with default count"""
        backend = GolfIMUBackend()
        backend.session_manager.get_swing_data = Mock(return_value=[])
        
        backend.get_recent_swings()
        
        backend.session_manager.get_swing_data.assert_called_once_with(count=5) 