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
    
    def test_backend_initialization(self, backend_with_mocks):
        """Test GolfIMUBackend initialization"""
        backend = backend_with_mocks
        
        assert backend.redis_manager is not None
        assert backend.serial_manager is not None
        assert backend.session_manager is not None
        assert backend.running is False
    
    def test_start_session_success(self, backend_with_mocks, mock_session):
        """Test successful session start"""
        backend = backend_with_mocks
        backend.session_manager.create_session = Mock(return_value=mock_session)
        
        result = backend.start_session(
            user_id="test_user",
            club_id="driver",
            club_length=1.07,
            club_mass=0.205
        )
        
        assert result is True
        backend.session_manager.create_session.assert_called_once()
    
    def test_start_session_failure(self, backend_with_mocks):
        """Test session start failure"""
        backend = backend_with_mocks
        backend.session_manager.create_session = Mock(side_effect=Exception("Session error"))
        
        result = backend.start_session(
            user_id="test_user",
            club_id="driver",
            club_length=1.07,
            club_mass=0.205
        )
        
        assert result is False
    
    def test_connect_arduino_success(self, backend_with_mocks):
        """Test successful Arduino connection"""
        backend = backend_with_mocks
        backend.serial_manager.connect = Mock(return_value=True)
        
        result = backend.connect_arduino("/dev/tty.test")
        
        assert result is True
        backend.serial_manager.connect.assert_called_once_with("/dev/tty.test")
    
    def test_connect_arduino_failure(self, backend_with_mocks):
        """Test Arduino connection failure"""
        backend = backend_with_mocks
        backend.serial_manager.connect = Mock(return_value=False)
        
        result = backend.connect_arduino("/dev/tty.test")
        
        assert result is False
    
    def test_connect_arduino_auto_detect(self, backend_with_mocks):
        """Test Arduino connection with auto-detection"""
        backend = backend_with_mocks
        backend.serial_manager.connect = Mock(return_value=True)
        
        result = backend.connect_arduino()
        
        assert result is True
        backend.serial_manager.connect.assert_called_once_with(None)
    
    def test_disconnect_arduino(self, backend_with_mocks):
        """Test Arduino disconnection"""
        backend = backend_with_mocks
        backend.serial_manager.disconnect = Mock()
        
        backend.disconnect_arduino()
        
        backend.serial_manager.disconnect.assert_called_once()
    
    def test_start_data_collection_no_session(self, backend_with_mocks):
        """Test starting data collection without session"""
        backend = backend_with_mocks
        backend.session_manager.get_current_session = Mock(return_value=None)
        
        backend.start_data_collection_c()
        
        # Should not start collection, no error should be raised
        assert backend.running is False
    
    def test_start_data_collection_no_arduino(self, backend_with_mocks, mock_session):
        """Test starting data collection without Arduino connection"""
        backend = backend_with_mocks
        backend.session_manager.get_current_session = Mock(return_value=mock_session)
        backend.serial_manager.is_connected = False
        
        backend.start_data_collection_c()
        
        assert backend.running is False
    
    @patch('subprocess.Popen')
    @patch('backend.main.time.sleep')
    @patch('builtins.open', create=True)
    @patch('os.path.exists')
    def test_start_data_collection_success(self, mock_exists, mock_open, mock_sleep, mock_popen, 
                                         backend_with_session_and_arduino, mock_process_that_stops, 
                                         mock_file_with_imu_data):
        """Test successful data collection start"""
        backend = backend_with_session_and_arduino
        
        # Mock C program process
        mock_popen.return_value = mock_process_that_stops
        
        # Mock file reading
        mock_open.return_value.__enter__.return_value = mock_file_with_imu_data
        
        # Mock os.path.exists for C program
        mock_exists.return_value = True
        
        # Mock signal handler to prevent sys.exit
        with patch('sys.exit'):
            # Start collection
            backend.start_data_collection_c()
        
        # Verify C program was started
        mock_popen.assert_called_once()
        assert backend.running is False  # Should stop after processing
    
    def test_detect_impact_above_threshold(self, backend_with_mocks, mock_session_with_impact_threshold, high_g_force_imu_data):
        """Test impact detection above threshold"""
        backend = backend_with_mocks
        
        # Mock session with impact threshold
        backend.session_manager.get_current_session = Mock(return_value=mock_session_with_impact_threshold)
        backend.session_manager.log_swing_event = Mock(return_value=Mock())
        
        backend._detect_impact(high_g_force_imu_data)
        
        # Should log impact event
        backend.session_manager.log_swing_event.assert_called_once()
        call_args = backend.session_manager.log_swing_event.call_args
        assert call_args[0][0] == "impact"
        assert "g_force" in call_args[0][1]
    
    def test_detect_impact_below_threshold(self, backend_with_mocks, mock_session_with_impact_threshold, low_g_force_imu_data):
        """Test impact detection below threshold"""
        backend = backend_with_mocks
        
        # Mock session with impact threshold
        backend.session_manager.get_current_session = Mock(return_value=mock_session_with_impact_threshold)
        backend.session_manager.log_swing_event = Mock(return_value=Mock())
        
        backend._detect_impact(low_g_force_imu_data)
        
        # Should not log impact event
        backend.session_manager.log_swing_event.assert_not_called()
    
    def test_detect_impact_no_session(self, backend_with_mocks, high_g_force_imu_data):
        """Test impact detection without session"""
        backend = backend_with_mocks
        backend.session_manager.get_current_session = Mock(return_value=None)
        backend.session_manager.log_swing_event = Mock()
        
        backend._detect_impact(high_g_force_imu_data)
        
        # Should not log impact event
        backend.session_manager.log_swing_event.assert_not_called()
    
    def test_stop(self, backend_with_mocks):
        """Test backend stop"""
        backend = backend_with_mocks
        backend.running = True
        backend.serial_manager.disconnect = Mock()
        
        backend.stop()
        
        assert backend.running is False
        backend.serial_manager.disconnect.assert_called_once()
    
    def test_get_status(self, backend_with_session_and_arduino):
        """Test getting backend status"""
        backend = backend_with_session_and_arduino
        
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
    
    def test_get_status_no_session(self, backend_with_mocks):
        """Test getting status without session"""
        backend = backend_with_mocks
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
    
    def test_get_session_summary(self, backend_with_mocks):
        """Test getting session summary"""
        backend = backend_with_mocks
        backend.session_manager.get_session_summary = Mock(return_value={"test": "summary"})
        
        summary = backend.get_session_summary()
        
        assert summary == {"test": "summary"}
        backend.session_manager.get_session_summary.assert_called_once()
    
    def test_signal_handler(self, backend_with_mocks):
        """Test signal handler"""
        backend = backend_with_mocks
        backend.stop = Mock()
        
        # Simulate signal handler call - should raise SystemExit
        with pytest.raises(SystemExit):
            backend._signal_handler(1, None)
        
        backend.stop.assert_called_once()
    
    def test_g_force_calculation(self, backend_with_mocks, mock_session_with_impact_threshold, high_g_force_imu_data):
        """Test g-force calculation in impact detection"""
        backend = backend_with_mocks
        
        # Mock session
        backend.session_manager.get_current_session = Mock(return_value=mock_session_with_impact_threshold)
        backend.session_manager.log_swing_event = Mock(return_value=Mock())
        
        backend._detect_impact(high_g_force_imu_data)
        
        # Should log impact event
        backend.session_manager.log_swing_event.assert_called_once()
        call_args = backend.session_manager.log_swing_event.call_args
        g_force = call_args[0][1]["g_force"]
        assert abs(g_force - 30.0) < 0.1  # Should be approximately 30g
    
    @patch('subprocess.Popen')
    @patch('backend.main.time.sleep')
    @patch('builtins.open', create=True)
    @patch('os.path.exists')
    def test_data_collection_interruption(self, mock_exists, mock_open, mock_sleep, mock_popen,
                                        backend_with_session_and_arduino, mock_process_that_stops, mock_file_empty):
        """Test data collection interruption"""
        backend = backend_with_session_and_arduino
        
        # Mock C program process
        mock_popen.return_value = mock_process_that_stops
        
        # Mock file reading
        mock_open.return_value.__enter__.return_value = mock_file_empty
        
        # Mock os.path.exists for C program
        mock_exists.return_value = True
        
        # Mock signal handler to prevent sys.exit
        with patch('sys.exit'):
            # Start collection
            backend.start_data_collection_c()
        
        # Should handle interruption gracefully
        assert backend.running is False
    
    @patch('subprocess.Popen')
    @patch('backend.main.time.sleep')
    @patch('builtins.open', create=True)
    @patch('os.path.exists')
    def test_data_collection_exception(self, mock_exists, mock_open, mock_sleep, mock_popen,
                                     backend_with_session_and_arduino, mock_file_empty):
        """Test data collection with exception"""
        backend = backend_with_session_and_arduino
        
        # Mock C program process that raises exception
        mock_process = Mock()
        mock_process.poll.side_effect = Exception("Process error")
        mock_popen.return_value = mock_process
        
        # Mock file reading
        mock_open.return_value.__enter__.return_value = mock_file_empty
        
        # Mock os.path.exists for C program
        mock_exists.return_value = True
        
        # Mock signal handler to prevent sys.exit
        with patch('sys.exit'):
            # Should handle exception gracefully
            backend.start_data_collection_c()
        
        assert backend.running is False
    
    def test_send_session_config_to_arduino_success(self, backend_with_session_and_arduino, mock_session):
        """Test successful session config sending to Arduino"""
        backend = backend_with_session_and_arduino
        backend.serial_manager.send_session_config = Mock(return_value=True)
        
        result = backend.send_session_config_to_arduino()
        
        assert result is True
        backend.serial_manager.send_session_config.assert_called_once_with(mock_session)
    
    def test_send_session_config_to_arduino_no_session(self, backend_with_mocks):
        """Test session config sending without session"""
        backend = backend_with_mocks
        backend.session_manager.get_current_session = Mock(return_value=None)
        
        result = backend.send_session_config_to_arduino()
        
        assert result is False
    
    def test_send_session_config_to_arduino_no_arduino(self, backend_with_session, mock_session):
        """Test session config sending without Arduino connection"""
        backend = backend_with_session
        backend.serial_manager.is_connected = False
        
        result = backend.send_session_config_to_arduino()
        
        assert result is False
    
    def test_start_swing_monitoring_success(self, backend_with_arduino_connected):
        """Test successful swing monitoring start"""
        backend = backend_with_arduino_connected
        backend.serial_manager.start_swing_monitoring = Mock(return_value=True)
        
        result = backend.start_swing_monitoring()
        
        assert result is True
        backend.serial_manager.start_swing_monitoring.assert_called_once()
    
    def test_start_swing_monitoring_no_arduino(self, backend_with_mocks):
        """Test swing monitoring start without Arduino connection"""
        backend = backend_with_mocks
        backend.serial_manager.is_connected = False
        
        result = backend.start_swing_monitoring()
        
        assert result is False
    
    def test_stop_swing_monitoring_success(self, backend_with_arduino_connected):
        """Test successful swing monitoring stop"""
        backend = backend_with_arduino_connected
        backend.serial_manager.stop_swing_monitoring = Mock(return_value=True)
        
        result = backend.stop_swing_monitoring()
        
        assert result is True
        backend.serial_manager.stop_swing_monitoring.assert_called_once()
    
    def test_stop_swing_monitoring_no_arduino(self, backend_with_mocks):
        """Test swing monitoring stop without Arduino connection"""
        backend = backend_with_mocks
        backend.serial_manager.is_connected = False
        
        result = backend.stop_swing_monitoring()
        
        assert result is False
    
    def test_wait_for_swing_data_success(self, backend_with_session_and_arduino, mock_session):
        """Test successful swing data waiting"""
        backend = backend_with_session_and_arduino
        
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
    
    def test_wait_for_swing_data_no_session(self, backend_with_mocks):
        """Test swing data waiting without session"""
        backend = backend_with_mocks
        backend.session_manager.get_current_session = Mock(return_value=None)
        
        result = backend.wait_for_swing_data()
        
        assert result is None
    
    def test_wait_for_swing_data_no_arduino(self, backend_with_session, mock_session):
        """Test swing data waiting without Arduino connection"""
        backend = backend_with_session
        backend.serial_manager.is_connected = False
        
        result = backend.wait_for_swing_data()
        
        assert result is None
    
    def test_wait_for_swing_data_no_data(self, backend_with_session_and_arduino, mock_session):
        """Test swing data waiting when no data received"""
        backend = backend_with_session_and_arduino
        backend.serial_manager.wait_for_swing_data = Mock(return_value=None)
        
        result = backend.wait_for_swing_data()
        
        assert result is None
    
    def test_wait_for_swing_data_storage_failure(self, backend_with_session_and_arduino, mock_session):
        """Test swing data waiting when storage fails"""
        backend = backend_with_session_and_arduino
        mock_swing_data = Mock()
        backend.serial_manager.wait_for_swing_data = Mock(return_value=mock_swing_data)
        backend.session_manager.store_swing_data = Mock(return_value=False)
        
        result = backend.wait_for_swing_data()
        
        assert result is None
    
    @patch('backend.main.time.sleep')
    def test_start_continuous_monitoring_success(self, mock_sleep, backend_with_session_and_arduino, mock_session):
        """Test successful continuous monitoring start"""
        backend = backend_with_session_and_arduino
        
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
    
    def test_start_continuous_monitoring_no_session(self, backend_with_mocks):
        """Test continuous monitoring without session"""
        backend = backend_with_mocks
        backend.session_manager.get_current_session = Mock(return_value=None)
        
        backend.start_continuous_monitoring()
        
        # Should return early without starting monitoring
        assert backend.running is False
    
    def test_start_continuous_monitoring_no_arduino(self, backend_with_session, mock_session):
        """Test continuous monitoring without Arduino connection"""
        backend = backend_with_session
        backend.serial_manager.is_connected = False
        
        backend.start_continuous_monitoring()
        
        # Should return early without starting monitoring
        assert backend.running is False
    
    def test_start_continuous_monitoring_config_failure(self, backend_with_session_and_arduino, mock_session):
        """Test continuous monitoring when config sending fails"""
        backend = backend_with_session_and_arduino
        backend.send_session_config_to_arduino = Mock(return_value=False)
        
        backend.start_continuous_monitoring()
        
        # Should return early without starting monitoring
        assert backend.running is False
    
    def test_start_continuous_monitoring_monitoring_failure(self, backend_with_session_and_arduino, mock_session):
        """Test continuous monitoring when monitoring start fails"""
        backend = backend_with_session_and_arduino
        backend.send_session_config_to_arduino = Mock(return_value=True)
        backend.start_swing_monitoring = Mock(return_value=False)
        
        backend.start_continuous_monitoring()
        
        # Should return early without starting monitoring
        assert backend.running is False
    
    def test_process_swing_data(self, backend_with_mocks):
        """Test swing data processing"""
        backend = backend_with_mocks
        
        # Create mock swing data
        mock_swing_data = Mock()
        mock_swing_data.swing_id = "test_swing"
        mock_swing_data.swing_duration = 1.5
        mock_swing_data.impact_g_force = 35.0
        mock_swing_data.imu_data_points = [Mock(), Mock(), Mock()]  # 3 data points
        
        # Mock print to capture output
        with patch('builtins.print') as mock_print:
            backend._process_swing_data(mock_swing_data)
        
        # Should print swing information
        mock_print.assert_called()
        # Check that it printed the swing ID
        calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("test_swing" in str(call) for call in calls)
    
    def test_get_swing_statistics(self, backend_with_mocks):
        """Test getting swing statistics"""
        backend = backend_with_mocks
        backend.session_manager.get_swing_statistics = Mock(return_value={"test": "stats"})
        
        result = backend.get_swing_statistics()
        
        assert result == {"test": "stats"}
        backend.session_manager.get_swing_statistics.assert_called_once()
    
    def test_get_recent_swings(self, backend_with_mocks):
        """Test getting recent swings"""
        backend = backend_with_mocks
        
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
    
    def test_get_recent_swings_default_count(self, backend_with_mocks):
        """Test getting recent swings with default count"""
        backend = backend_with_mocks
        backend.session_manager.get_swing_data = Mock(return_value=[])
        
        backend.get_recent_swings()
        
        backend.session_manager.get_swing_data.assert_called_once_with(count=5) 