"""
Serial manager for GolfIMU backend
"""
import serial
import serial.tools.list_ports
import time
from typing import Optional, List
import json
from datetime import datetime

from .config import settings
from .models import IMUData, SwingData


class SerialManager:
    """Manages serial communication with Arduino IMU"""
    
    def __init__(self):
        """Initialize serial manager"""
        self.serial_connection: Optional[serial.Serial] = None
        self.is_connected = False
    
    def find_arduino_port(self) -> Optional[str]:
        """Find Arduino port automatically.
        
        Returns:
            Port name if found, None otherwise
        """
        ports = serial.tools.list_ports.comports()
        
        for port in ports:
            # Common Arduino identifiers
            if any(identifier in port.description.lower() for identifier in [
                'arduino', 'usb serial', 'ch340', 'cp210x', 'ftdi'
            ]):
                return port.device
        
        return None
    
    def connect(self, port: Optional[str] = None) -> bool:
        """Connect to Arduino via serial.
        
        Args:
            port: Serial port to connect to (auto-detect if None)
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            if port is None:
                port = self.find_arduino_port()
                if port is None:
                    print("No Arduino port found automatically")
                    return False
            
            self.serial_connection = serial.Serial(
                port=port,
                baudrate=settings.serial_baudrate,
                timeout=settings.serial_timeout
            )
            
            # Wait for connection to stabilize
            time.sleep(2)
            
            self.is_connected = True
            print(f"Connected to Arduino on {port}")
            return True
            
        except Exception as e:
            print(f"Error connecting to Arduino: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Disconnect from Arduino"""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        self.is_connected = False
        print("Disconnected from Arduino")
    
    def wait_for_swing_data(self) -> Optional[SwingData]:
        """Wait for complete swing data from Arduino.
        
        Returns:
            SwingData object if received, None otherwise
        """
        if not self.is_connected or not self.serial_connection:
            print("Not connected to Arduino - cannot wait for swing data")
            return None
        
        try:
            # Wait for swing data transmission with timeout
            # Arduino will send a complete swing after impact detection
            line = self.serial_connection.readline().decode('utf-8').strip()
            
            if not line:
                return None
            
            # Parse swing data (JSON format from Arduino)
            swing_dict = json.loads(line)
            
            # Parse IMU data points
            imu_data_points = []
            for imu_dict in swing_dict["imu_data_points"]:
                imu_data = IMUData(
                    ax=imu_dict["ax"],
                    ay=imu_dict["ay"],
                    az=imu_dict["az"],
                    gx=imu_dict["gx"],
                    gy=imu_dict["gy"],
                    gz=imu_dict["gz"],
                    mx=imu_dict["mx"],
                    my=imu_dict["my"],
                    mz=imu_dict["mz"],
                    qw=imu_dict["qw"],
                    qx=imu_dict["qx"],
                    qy=imu_dict["qy"],
                    qz=imu_dict["qz"],
                    timestamp=datetime.fromisoformat(imu_dict["timestamp"])
                )
                imu_data_points.append(imu_data)
            
            # Create SwingData object
            swing_data = SwingData(
                swing_id=swing_dict["swing_id"],
                session_id=swing_dict["session_id"],
                imu_data_points=imu_data_points,
                swing_start_time=datetime.fromisoformat(swing_dict["swing_start_time"]),
                swing_end_time=datetime.fromisoformat(swing_dict["swing_end_time"]),
                swing_duration=swing_dict["swing_duration"],
                impact_g_force=swing_dict["impact_g_force"],
                swing_type=swing_dict.get("swing_type", "full_swing")
            )
            
            return swing_data
            
        except json.JSONDecodeError as e:
            print(f"Error parsing swing data JSON: {e}")
            return None
        except KeyError as e:
            print(f"Missing required field in swing data: {e}")
            return None
        except Exception as e:
            print(f"Error reading swing data: {e}")
            return None
    
    def send_session_config(self, session_config) -> bool:
        """Send session configuration to Arduino.
        
        Args:
            session_config: Session configuration to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_connected or not self.serial_connection:
            return False
        
        try:
            config_data = {
                "session_id": session_config.session_id,
                "user_id": session_config.user_id,
                "club_id": session_config.club_id,
                "club_length": session_config.club_length,
                "club_mass": session_config.club_mass,
                "impact_threshold": session_config.impact_threshold
            }
            
            config_json = json.dumps(config_data)
            self.serial_connection.write(f"CONFIG:{config_json}\n".encode('utf-8'))
            return True
            
        except Exception as e:
            print(f"Error sending session config: {e}")
            return False
    
    def send_command(self, command: str) -> bool:
        """Send command to Arduino.
        
        Args:
            command: Command string to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_connected or not self.serial_connection:
            return False
        
        try:
            self.serial_connection.write(f"{command}\n".encode('utf-8'))
            return True
        except Exception as e:
            print(f"Error sending command: {e}")
            return False
    
    def get_connection_status(self) -> tuple[bool, Optional[str]]:
        """Get connection status and port info.
        
        Returns:
            Tuple of (connected, port_name)
        """
        if self.is_connected and self.serial_connection:
            return True, self.serial_connection.port
        return False, None
    
    def start_swing_monitoring(self) -> bool:
        """Start swing monitoring on Arduino.
        
        Returns:
            True if command sent successfully, False otherwise
        """
        return self.send_command("START_MONITORING")
    
    def stop_swing_monitoring(self) -> bool:
        """Stop swing monitoring on Arduino.
        
        Returns:
            True if command sent successfully, False otherwise
        """
        return self.send_command("STOP_MONITORING")
    
    def request_swing_data(self) -> bool:
        """Request swing data from Arduino.
        
        Returns:
            True if command sent successfully, False otherwise
        """
        return self.send_command("REQUEST_SWING")

    def read_imu_data(self) -> Optional[IMUData]:
        """Read single IMU data point from Arduino (expects JSON line)
        
        Returns:
            IMUData object if valid data received, None otherwise
        """
        if not self.is_connected or not self.serial_connection:
            return None
        
        try:
            # Use timeout to prevent blocking indefinitely
            line = self.serial_connection.readline().decode('utf-8').strip()
            if not line:
                return None
            
            # Skip non-JSON lines (startup messages, command responses, etc.)
            if not line.startswith('{') or not line.endswith('}'):
                return None
            
            # Parse IMU data (JSON format) - optimized for speed
            imu_dict = json.loads(line)
            
            # Use current time directly - minimal overhead
            timestamp = datetime.now()
            
            return IMUData(
                ax=imu_dict["ax"],
                ay=imu_dict["ay"],
                az=imu_dict["az"],
                gx=imu_dict["gx"],
                gy=imu_dict["gy"],
                gz=imu_dict["gz"],
                mx=imu_dict["mx"],
                my=imu_dict["my"],
                mz=imu_dict["mz"],
                qw=imu_dict["qw"],
                qx=imu_dict["qx"],
                qy=imu_dict["qy"],
                qz=imu_dict["qz"],
                timestamp=timestamp
            )
        
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            # Only print error for lines that look like JSON but failed to parse
            if line.startswith('{') and line.endswith('}'):
                print(f"Error parsing IMU data: {e}")
            return None
        except Exception as e:
            print(f"Error reading IMU data: {e}")
            return None

    def imu_data_stream(self):
        """Generator that yields IMU data continuously.
        
        Yields:
            IMUData objects as they are received
        """
        if not self.is_connected or not self.serial_connection:
            return
        
        try:
            while self.is_connected:
                imu_data = self.read_imu_data()
                if imu_data is not None:
                    yield imu_data
                else:
                    # Small delay to prevent busy waiting
                    time.sleep(0.001)
        except Exception as e:
            print(f"Error in IMU data stream: {e}")
            return



 