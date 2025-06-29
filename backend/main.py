"""
Main GolfIMU backend application
"""
import time
import signal
import sys
from typing import Optional

from .config import settings
from .redis_manager import RedisManager
from .serial_manager import SerialManager
from .session_manager import SessionManager
from .models import IMUData, SessionConfig, SwingData


class GolfIMUBackend:
    """Main GolfIMU backend application"""
    
    def __init__(self):
        """Initialize the backend"""
        self.redis_manager = RedisManager()
        self.serial_manager = SerialManager()
        self.session_manager = SessionManager(self.redis_manager)
        self.running = False
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print("\nShutting down GolfIMU backend...")
        self.stop()
        sys.exit(0)
    
    def start_session(self, 
                     user_id: str,
                     club_id: str,
                     club_length: float,
                     club_mass: float,
                     face_normal_calibration: Optional[list] = None,
                     impact_threshold: Optional[float] = None) -> bool:
        """Start a new session"""
        try:
            session_config = self.session_manager.create_session(
                user_id=user_id,
                club_id=club_id,
                club_length=club_length,
                club_mass=club_mass,
                face_normal_calibration=face_normal_calibration,
                impact_threshold=impact_threshold
            )
            print(f"Session started: {session_config.session_id}")
            return True
        except Exception as e:
            print(f"Failed to start session: {e}")
            return False
    
    def connect_arduino(self, port: Optional[str] = None) -> bool:
        """Connect to Arduino"""
        return self.serial_manager.connect(port)
    
    def disconnect_arduino(self):
        """Disconnect from Arduino"""
        self.serial_manager.disconnect()
    
    def send_session_config_to_arduino(self) -> bool:
        """Send current session configuration to Arduino"""
        if not self.session_manager.get_current_session():
            print("No active session. Please start a session first.")
            return False
        
        if not self.serial_manager.is_connected:
            print("Arduino not connected. Please connect first.")
            return False
        
        return self.serial_manager.send_session_config(self.session_manager.get_current_session())
    
    def start_swing_monitoring(self) -> bool:
        """Start swing monitoring on Arduino"""
        if not self.serial_manager.is_connected:
            print("Arduino not connected. Please connect first.")
            return False
        
        return self.serial_manager.start_swing_monitoring()
    
    def stop_swing_monitoring(self) -> bool:
        """Stop swing monitoring on Arduino"""
        if not self.serial_manager.is_connected:
            print("Arduino not connected. Please connect first.")
            return False
        
        return self.serial_manager.stop_swing_monitoring()
    
    def wait_for_swing_data(self) -> Optional[SwingData]:
        """Wait for complete swing data from Arduino"""
        if not self.session_manager.get_current_session():
            print("No active session. Please start a session first.")
            return None
        
        if not self.serial_manager.is_connected:
            print("Arduino not connected. Please connect first.")
            return None
        
        print("Waiting for swing data from Arduino...")
        swing_data = self.serial_manager.wait_for_swing_data()
        
        if swing_data:
            # Store swing data in Redis
            if self.session_manager.store_swing_data(swing_data):
                print(f"Received and stored swing: {swing_data.swing_id}")
                print(f"Swing duration: {swing_data.swing_duration:.2f}s")
                print(f"Impact g-force: {swing_data.impact_g_force:.1f}g")
                print(f"Data points: {len(swing_data.imu_data_points)}")
                return swing_data
            else:
                print("Failed to store swing data")
                return None
        else:
            print("No swing data received")
            return None
    
    def start_continuous_monitoring(self):
        """Start continuous swing monitoring"""
        if not self.session_manager.get_current_session():
            print("No active session. Please start a session first.")
            return
        
        if not self.serial_manager.is_connected:
            print("Arduino not connected. Please connect first.")
            return
        
        print("Starting continuous swing monitoring...")
        self.running = True
        
        # Send session config to Arduino
        if not self.send_session_config_to_arduino():
            print("Failed to send session config to Arduino")
            self.running = False
            return
        
        # Start monitoring on Arduino
        if not self.start_swing_monitoring():
            print("Failed to start swing monitoring on Arduino")
            self.running = False
            return
        
        try:
            while self.running:
                swing_data = self.wait_for_swing_data()
                if swing_data:
                    # Process swing data (placeholder for analyzer functions)
                    self._process_swing_data(swing_data)
                else:
                    # No swing data received, continue waiting
                    time.sleep(0.1)
                    
        except KeyboardInterrupt:
            print("\nContinuous monitoring stopped by user")
        except Exception as e:
            print(f"Error during continuous monitoring: {e}")
        finally:
            self.running = False
            self.stop_swing_monitoring()
    
    def _process_swing_data(self, swing_data: SwingData):
        """Process swing data (placeholder for analyzer functions)"""
        # This is where you'll add your analyzer functions
        # For now, just log some basic info
        print(f"Processing swing: {swing_data.swing_id}")
        print(f"  Duration: {swing_data.swing_duration:.2f}s")
        print(f"  Impact g-force: {swing_data.impact_g_force:.1f}g")
        print(f"  Data points: {len(swing_data.imu_data_points)}")
        
        # Log swing event
        self.session_manager.log_swing_event("swing_completed", {
            "swing_id": swing_data.swing_id,
            "duration": swing_data.swing_duration,
            "impact_g_force": swing_data.impact_g_force,
            "data_points": len(swing_data.imu_data_points)
        })
    
    def stop(self):
        """Stop the backend"""
        self.running = False
        self.stop_swing_monitoring()
        self.disconnect_arduino()
        print("GolfIMU backend stopped")
    
    def get_status(self) -> dict:
        """Get backend status"""
        arduino_connected, arduino_port = self.serial_manager.get_connection_status()
        current_session = self.session_manager.get_current_session()
        
        return {
            "arduino_connected": arduino_connected,
            "arduino_port": arduino_port,
            "session_active": current_session is not None,
            "session_id": current_session.session_id if current_session else None,
            "user_id": current_session.user_id if current_session else None,
            "club_id": current_session.club_id if current_session else None,
            "monitoring_running": self.running,
            "data_collection_running": self.running
        }
    
    def get_session_summary(self) -> dict:
        """Get current session summary"""
        return self.session_manager.get_session_summary()
    
    def get_swing_statistics(self) -> dict:
        """Get swing statistics for current session"""
        return self.session_manager.get_swing_statistics()
    
    def get_recent_swings(self, count: int = 5) -> list:
        """Get recent swings for current session"""
        swings = self.session_manager.get_swing_data(count=count)
        return [
            {
                "swing_id": swing.swing_id,
                "duration": swing.swing_duration,
                "impact_g_force": swing.impact_g_force,
                "swing_type": swing.swing_type,
                "data_points": len(swing.imu_data_points),
                "start_time": swing.swing_start_time.isoformat(),
                "end_time": swing.swing_end_time.isoformat()
            }
            for swing in swings
        ]

    def start_data_collection(self):
        """Start data collection from Arduino"""
        if not self.session_manager.get_current_session():
            print("No active session. Please start a session first.")
            return
        
        if not self.serial_manager.is_connected:
            print("Arduino not connected. Please connect first.")
            return
        
        print("Starting data collection...")
        self.running = True
        
        try:
            for imu_data in self.serial_manager.imu_data_stream():
                if imu_data:
                    # Store IMU data
                    if self.redis_manager.store_imu_data(imu_data, self.session_manager.get_current_session()):
                        # Check for impact detection
                        self._detect_impact(imu_data)
                else:
                    # No data received, continue
                    time.sleep(0.01)
                    
        except KeyboardInterrupt:
            print("\nData collection stopped by user")
        except Exception as e:
            print(f"Error during data collection: {e}")
        finally:
            self.running = False

    def _detect_impact(self, imu_data: IMUData):
        """Detect impact based on acceleration threshold"""
        current_session = self.session_manager.get_current_session()
        if not current_session:
            return
        
        # Calculate acceleration magnitude
        accel_magnitude = (imu_data.ax**2 + imu_data.ay**2 + imu_data.az**2)**0.5
        
        # Convert to g-force (divide by 9.81 m/s²)
        g_force = accel_magnitude / 9.81
        
        # Check if impact threshold is exceeded
        if g_force >= current_session.impact_threshold:
            # Log impact event
            self.session_manager.log_swing_event("impact", {
                "g_force": g_force,
                "timestamp": imu_data.timestamp.isoformat(),
                "accel_magnitude": accel_magnitude
            })
            print(f"Impact detected! G-force: {g_force:.1f}g")


def main():
    """Main entry point"""
    print("GolfIMU Backend Starting...")
    
    backend = GolfIMUBackend()
    
    # Example usage - you can modify this or create a proper CLI interface
    print("\nGolfIMU Backend Ready!")
    print("Available commands:")
    print("  start_session <user_id> <club_id> <club_length> <club_mass>")
    print("  connect_arduino [port]")
    print("  send_config")
    print("  start_monitoring")
    print("  wait_swing")
    print("  continuous_monitoring")
    print("  status")
    print("  summary")
    print("  statistics")
    print("  recent_swings [count]")
    print("  quit")
    
    while True:
        try:
            command = input("\n> ").strip().split()
            if not command:
                continue
            
            cmd = command[0].lower()
            
            if cmd == "start_session" and len(command) >= 5:
                user_id = command[1]
                club_id = command[2]
                club_length = float(command[3])
                club_mass = float(command[4])
                
                backend.start_session(user_id, club_id, club_length, club_mass)
            
            elif cmd == "connect_arduino":
                port = command[1] if len(command) > 1 else None
                if backend.connect_arduino(port):
                    print("Arduino connected successfully")
                else:
                    print("Failed to connect to Arduino")
            
            elif cmd == "send_config":
                if backend.send_session_config_to_arduino():
                    print("Session config sent to Arduino")
                else:
                    print("Failed to send session config")
            
            elif cmd == "start_monitoring":
                if backend.start_swing_monitoring():
                    print("Swing monitoring started on Arduino")
                else:
                    print("Failed to start swing monitoring")
            
            elif cmd == "wait_swing":
                swing_data = backend.wait_for_swing_data()
                if swing_data:
                    print(f"Received swing: {swing_data.swing_id}")
                else:
                    print("No swing data received")
            
            elif cmd == "continuous_monitoring":
                backend.start_continuous_monitoring()
            
            elif cmd == "status":
                status = backend.get_status()
                for key, value in status.items():
                    print(f"  {key}: {value}")
            
            elif cmd == "summary":
                summary = backend.get_session_summary()
                for key, value in summary.items():
                    print(f"  {key}: {value}")
            
            elif cmd == "statistics":
                stats = backend.get_swing_statistics()
                for key, value in stats.items():
                    print(f"  {key}: {value}")
            
            elif cmd == "recent_swings":
                count = int(command[1]) if len(command) > 1 else 5
                swings = backend.get_recent_swings(count)
                for i, swing in enumerate(swings, 1):
                    print(f"  Swing {i}: {swing['swing_id'][:8]}... - {swing['duration']:.2f}s - {swing['impact_g_force']:.1f}g")
            
            elif cmd == "quit":
                backend.stop()
                break
            
            else:
                print("Unknown command. Type 'quit' to exit.")
        
        except KeyboardInterrupt:
            backend.stop()
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main() 