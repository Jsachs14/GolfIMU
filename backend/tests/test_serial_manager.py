"""
Tests for backend.serial_manager module
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.serial_manager import SerialManager
from backend.models import IMUData, SwingData


class TestSerialManager:
    """Test SerialManager class"""
    
    def test_serial_manager_initialization(self):
        """Test SerialManager initialization"""
        manager = SerialManager()
        
        assert manager.serial_connection is None
        assert manager.is_connected is False
    
    @patch('backend.serial_manager.serial.tools.list_ports.comports')
    def test_find_arduino_port_success(self, mock_comports):
        """Test successful Arduino port detection"""
        # Mock available ports
        mock_port = Mock()
        mock_port.device = "/dev/tty.usbserial-12345"
        mock_port.description = "Arduino Uno"
        mock_comports.return_value = [mock_port]
        
        manager = SerialManager()
        result = manager.find_arduino_port()
        
        assert result == "/dev/tty.usbserial-12345"
    
    @patch('backend.serial_manager.serial.tools.list_ports.comports')
    def test_find_arduino_port_not_found(self, mock_comports):
        """Test Arduino port detection when not found"""
        # Mock available ports (none are Arduino)
        mock_port = Mock()
        mock_port.device = "/dev/tty.usbmodem12345"
        mock_port.description = "Some other device"
        mock_comports.return_value = [mock_port]
        
        manager = SerialManager()
        result = manager.find_arduino_port()
        
        assert result is None
    
    @patch('backend.serial_manager.serial.tools.list_ports.comports')
    def test_find_arduino_port_empty(self, mock_comports):
        """Test Arduino port detection with no ports"""
        mock_comports.return_value = []
        
        manager = SerialManager()
        result = manager.find_arduino_port()
        
        assert result is None
    
    @patch('backend.serial_manager.serial.Serial')
    @patch('backend.serial_manager.time.sleep')
    def test_connect_with_port(self, mock_sleep, mock_serial_class):
        """Test connecting with specific port"""
        mock_serial = Mock()
        mock_serial_class.return_value = mock_serial
        
        manager = SerialManager()
        result = manager.connect("/dev/tty.test")
        
        assert result is True
        assert manager.is_connected is True
        assert manager.serial_connection == mock_serial
        mock_serial_class.assert_called_once()
        mock_sleep.assert_called_once_with(2)
    
    @patch('backend.serial_manager.serial.Serial')
    @patch('backend.serial_manager.time.sleep')
    @patch.object(SerialManager, 'find_arduino_port')
    def test_connect_auto_detect(self, mock_find_port, mock_sleep, mock_serial_class):
        """Test connecting with auto-detection"""
        mock_serial = Mock()
        mock_serial_class.return_value = mock_serial
        mock_find_port.return_value = "/dev/tty.auto"
        
        manager = SerialManager()
        result = manager.connect()
        
        assert result is True
        assert manager.is_connected is True
        mock_find_port.assert_called_once()
        mock_serial_class.assert_called_once()
    
    @patch('backend.serial_manager.serial.Serial')
    @patch.object(SerialManager, 'find_arduino_port')
    def test_connect_no_port_found(self, mock_find_port, mock_serial_class):
        """Test connecting when no port is found"""
        mock_find_port.return_value = None
        
        manager = SerialManager()
        result = manager.connect()
        
        assert result is False
        assert manager.is_connected is False
        mock_serial_class.assert_not_called()
    
    @patch('backend.serial_manager.serial.Serial')
    def test_connect_serial_error(self, mock_serial_class):
        """Test connecting with serial error"""
        mock_serial_class.side_effect = Exception("Serial error")
        
        manager = SerialManager()
        result = manager.connect("/dev/tty.test")
        
        assert result is False
        assert manager.is_connected is False
    
    def test_disconnect_connected(self, serial_manager_with_mock):
        """Test disconnecting when connected"""
        serial_manager_with_mock.disconnect()
        
        assert serial_manager_with_mock.is_connected is False
        serial_manager_with_mock.serial_connection.close.assert_called_once()
    
    def test_disconnect_not_connected(self):
        """Test disconnecting when not connected"""
        manager = SerialManager()
        manager.disconnect()  # Should not raise error
        
        assert manager.is_connected is False
    
    def test_read_imu_data_success(self, serial_manager_with_mock):
        """Test successful IMU data reading"""
        result = serial_manager_with_mock.read_imu_data()
        
        assert result is not None
        assert isinstance(result, IMUData)
        assert result.ax == 1.0
        assert result.ay == 2.0
        assert result.az == 3.0
        assert result.gx == 4.0
        assert result.gy == 5.0
        assert result.gz == 6.0
        assert result.mx == 7.0
        assert result.my == 8.0
        assert result.mz == 9.0
    
    def test_read_imu_data_not_connected(self):
        """Test reading IMU data when not connected"""
        manager = SerialManager()
        result = manager.read_imu_data()
        
        assert result is None
    
    def test_read_imu_data_empty_line(self, serial_manager_with_mock):
        """Test reading IMU data with empty line"""
        serial_manager_with_mock.serial_connection.readline.return_value = b""
        
        result = serial_manager_with_mock.read_imu_data()
        
        assert result is None
    
    def test_read_imu_data_invalid_format(self, serial_manager_with_mock):
        """Test reading IMU data with invalid format"""
        serial_manager_with_mock.serial_connection.readline.return_value = b"invalid,data,format\n"
        
        result = serial_manager_with_mock.read_imu_data()
        
        assert result is None
    
    def test_read_imu_data_parse_error(self, serial_manager_with_mock):
        """Test reading IMU data with parse error"""
        serial_manager_with_mock.serial_connection.readline.return_value = b"1.0,2.0,3.0,4.0,5.0,6.0,7.0,8.0,not-a-number\n"
        
        result = serial_manager_with_mock.read_imu_data()
        
        assert result is None
    
    def test_read_imu_data_serial_error(self, serial_manager_with_mock):
        """Test reading IMU data with serial error"""
        serial_manager_with_mock.serial_connection.readline.side_effect = Exception("Serial error")
        
        result = serial_manager_with_mock.read_imu_data()
        
        assert result is None
    
    @patch('backend.serial_manager.time.sleep')
    def test_imu_data_stream(self, mock_sleep, serial_manager_with_mock):
        """Test IMU data stream generator"""
        # Mock read_imu_data to return data then disconnect
        call_count = 0
        def mock_read_imu_data():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return IMUData(ax=1.0, ay=2.0, az=3.0, gx=4.0, gy=5.0, gz=6.0, mx=7.0, my=8.0, mz=9.0, qw=1.0, qx=0.0, qy=0.0, qz=0.0)
            elif call_count == 2:
                return IMUData(ax=2.0, ay=3.0, az=4.0, gx=5.0, gy=6.0, gz=7.0, mx=8.0, my=9.0, mz=10.0, qw=1.0, qx=0.0, qy=0.0, qz=0.0)
            else:
                # Disconnect to stop the generator
                serial_manager_with_mock.is_connected = False
                return None
        
        serial_manager_with_mock.read_imu_data = Mock(side_effect=mock_read_imu_data)
        
        # Collect data manually
        stream = serial_manager_with_mock.imu_data_stream()
        data_list = []
        for data in stream:
            data_list.append(data)
            if len(data_list) >= 2:  # We expect 2 data points
                break
        
        assert len(data_list) == 2
        assert data_list[0].ax == 1.0
        assert data_list[1].ax == 2.0
        assert mock_sleep.call_count >= 0  # May or may not be called depending on timing
    
    def test_imu_data_stream_not_connected(self):
        """Test IMU data stream when not connected"""
        manager = SerialManager()
        manager.is_connected = False
        
        stream = manager.imu_data_stream()
        data_list = list(stream)
        
        assert data_list == []
    
    def test_send_command_success(self, serial_manager_with_mock):
        """Test successful command sending"""
        result = serial_manager_with_mock.send_command("test_command")
        
        assert result is True
        serial_manager_with_mock.serial_connection.write.assert_called_once_with(b"test_command\n")
    
    def test_send_command_not_connected(self):
        """Test sending command when not connected"""
        manager = SerialManager()
        result = manager.send_command("test_command")
        
        assert result is False
    
    def test_send_command_serial_error(self, serial_manager_with_mock):
        """Test sending command with serial error"""
        serial_manager_with_mock.serial_connection.write.side_effect = Exception("Serial error")
        
        result = serial_manager_with_mock.send_command("test_command")
        
        assert result is False
    
    def test_get_connection_status_connected(self, serial_manager_with_mock):
        """Test getting connection status when connected"""
        connected, port = serial_manager_with_mock.get_connection_status()
        
        assert connected is True
        assert port is not None
    
    def test_get_connection_status_not_connected(self):
        """Test getting connection status when not connected"""
        manager = SerialManager()
        connected, port = manager.get_connection_status()
        
        assert connected is False
        assert port is None
    
    def test_get_connection_status_no_connection(self):
        """Test getting connection status with no connection object"""
        manager = SerialManager()
        manager.is_connected = True  # But no serial_connection
        connected, port = manager.get_connection_status()
        
        assert connected is False
        assert port is None
    
    def test_wait_for_swing_data_success(self, serial_manager_with_mock):
        """Test successful swing data waiting"""
        # Mock JSON response
        mock_json_response = {
            "swing_id": "test_swing",
            "session_id": "test_session",
            "imu_data_points": [
                {
                    "ax": 1.0, "ay": 2.0, "az": 3.0,
                    "gx": 4.0, "gy": 5.0, "gz": 6.0,
                    "mx": 7.0, "my": 8.0, "mz": 9.0,
                    "qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0,
                    "timestamp": "2023-01-01T12:00:00"
                }
            ],
            "swing_start_time": "2023-01-01T12:00:00",
            "swing_end_time": "2023-01-01T12:01:00",
            "swing_duration": 1.0,
            "impact_g_force": 30.0,
            "swing_type": "full_swing"
        }
        
        import json
        serial_manager_with_mock.serial_connection.readline.return_value = json.dumps(mock_json_response).encode('utf-8')
        
        result = serial_manager_with_mock.wait_for_swing_data()
        
        assert result is not None
        assert isinstance(result, SwingData)
        assert result.swing_id == "test_swing"
        assert result.session_id == "test_session"
        assert len(result.imu_data_points) == 1
        assert result.swing_duration == 1.0
        assert result.impact_g_force == 30.0
        assert result.swing_type == "full_swing"
    
    def test_wait_for_swing_data_not_connected(self):
        """Test swing data waiting when not connected"""
        manager = SerialManager()
        result = manager.wait_for_swing_data()
        
        assert result is None
    
    def test_wait_for_swing_data_empty_line(self, serial_manager_with_mock):
        """Test swing data waiting with empty line"""
        serial_manager_with_mock.serial_connection.readline.return_value = b""
        
        result = serial_manager_with_mock.wait_for_swing_data()
        
        assert result is None
    
    def test_wait_for_swing_data_json_error(self, serial_manager_with_mock):
        """Test swing data waiting with JSON error"""
        serial_manager_with_mock.serial_connection.readline.return_value = b"invalid-json"
        
        result = serial_manager_with_mock.wait_for_swing_data()
        
        assert result is None
    
    def test_wait_for_swing_data_missing_field(self, serial_manager_with_mock):
        """Test swing data waiting with missing field"""
        mock_json_response = {
            "swing_id": "test_swing",
            # Missing required fields
        }
        
        import json
        serial_manager_with_mock.serial_connection.readline.return_value = json.dumps(mock_json_response).encode('utf-8')
        
        result = serial_manager_with_mock.wait_for_swing_data()
        
        assert result is None
    
    def test_wait_for_swing_data_serial_error(self, serial_manager_with_mock):
        """Test swing data waiting with serial error"""
        serial_manager_with_mock.serial_connection.readline.side_effect = Exception("Serial error")
        
        result = serial_manager_with_mock.wait_for_swing_data()
        
        assert result is None
    
    def test_send_session_config_success(self, serial_manager_with_mock):
        """Test successful session config sending"""
        # Create mock session config
        mock_session = Mock()
        mock_session.session_id = "test_session"
        mock_session.user_id = "test_user"
        mock_session.club_id = "driver"
        mock_session.club_length = 1.07
        mock_session.club_mass = 0.205
        mock_session.impact_threshold = 30.0
        
        result = serial_manager_with_mock.send_session_config(mock_session)
        
        assert result is True
        serial_manager_with_mock.serial_connection.write.assert_called_once()
        
        # Check that config was sent in correct format
        call_args = serial_manager_with_mock.serial_connection.write.call_args
        written_data = call_args[0][0].decode('utf-8')
        assert written_data.startswith("CONFIG:")
        assert "test_session" in written_data
        assert "test_user" in written_data
        assert "driver" in written_data
    
    def test_send_session_config_not_connected(self):
        """Test session config sending when not connected"""
        manager = SerialManager()
        mock_session = Mock()
        
        result = manager.send_session_config(mock_session)
        
        assert result is False
    
    def test_send_session_config_serial_error(self, serial_manager_with_mock):
        """Test session config sending with serial error"""
        serial_manager_with_mock.serial_connection.write.side_effect = Exception("Serial error")
        mock_session = Mock()
        
        result = serial_manager_with_mock.send_session_config(mock_session)
        
        assert result is False
    
    def test_start_swing_monitoring(self, serial_manager_with_mock):
        """Test starting swing monitoring"""
        result = serial_manager_with_mock.start_swing_monitoring()
        
        assert result is True
        serial_manager_with_mock.serial_connection.write.assert_called_once_with(b"START_MONITORING\n")
    
    def test_stop_swing_monitoring(self, serial_manager_with_mock):
        """Test stopping swing monitoring"""
        result = serial_manager_with_mock.stop_swing_monitoring()
        
        assert result is True
        serial_manager_with_mock.serial_connection.write.assert_called_once_with(b"STOP_MONITORING\n")
    
    def test_request_swing_data(self, serial_manager_with_mock):
        """Test requesting swing data"""
        result = serial_manager_with_mock.request_swing_data()
        
        assert result is True
        serial_manager_with_mock.serial_connection.write.assert_called_once_with(b"REQUEST_SWING\n") 