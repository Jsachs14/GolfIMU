#!/usr/bin/env python3
"""
GolfIMU System Runner
Runs both embedded system (Arduino) and backend together with proper thread management.
"""

import os
import sys
import time
import signal
import threading
import subprocess
import queue
import json
from pathlib import Path
from typing import Optional, Dict, Any
import logging

# Add scripts directory to path for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

# Import common utilities
from utils import setup_project_paths, verify_project_structure

# Setup project paths
project_root = setup_project_paths()

# Import global configuration
from global_config import *

from backend.main import GolfIMUBackend
from backend.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class GolfIMUSystemRunner:
    """Main system runner that coordinates embedded and backend systems"""
    
    def __init__(self):
        """Initialize the system runner"""
        self.backend = GolfIMUBackend()
        self.redis_process: Optional[subprocess.Popen] = None
        self.arduino_monitor_process: Optional[subprocess.Popen] = None
        self.running = False
        self.command_queue = queue.Queue()
        self.status_lock = threading.Lock()
        
        # Thread-safe status tracking
        self.system_status = {
            'redis_running': False,
            'arduino_connected': False,
            'backend_running': False,
            'session_active': False,
            'monitoring_active': False
        }
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("Received shutdown signal, stopping GolfIMU system...")
        self.stop()
        sys.exit(0)
    
    def _update_status(self, key: str, value: Any):
        """Thread-safe status update"""
        with self.status_lock:
            self.system_status[key] = value
    
    def start_redis(self) -> bool:
        """Start Redis server with persistence"""
        try:
            redis_conf_path = project_root / "redis.conf"
            if not redis_conf_path.exists():
                logger.error(f"Redis config file not found: {redis_conf_path}")
                return False
            
            # Check if Redis is already running
            try:
                result = subprocess.run(['redis-cli', 'ping'], 
                                      capture_output=True, text=True, timeout=2)
                if result.returncode == 0 and 'PONG' in result.stdout:
                    logger.info("Redis is already running")
                    self._update_status('redis_running', True)
                    return True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            
            # Start Redis server
            logger.info("Starting Redis server...")
            self.redis_process = subprocess.Popen(
                ['redis-server', str(redis_conf_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for Redis to start
            time.sleep(3)
            
            # Verify Redis is running
            try:
                result = subprocess.run(['redis-cli', 'ping'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and 'PONG' in result.stdout:
                    logger.info("Redis server started successfully")
                    self._update_status('redis_running', True)
                    return True
                else:
                    logger.error("Redis server failed to start")
                    return False
            except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                logger.error(f"Failed to verify Redis: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting Redis: {e}")
            return False
    
    def stop_redis(self):
        """Stop Redis server"""
        if self.redis_process:
            logger.info("Stopping Redis server...")
            self.redis_process.terminate()
            try:
                self.redis_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("Redis didn't stop gracefully, forcing...")
                self.redis_process.kill()
            self.redis_process = None
            self._update_status('redis_running', False)
    
    def connect_arduino(self, port: Optional[str] = None) -> bool:
        """Connect to Arduino with retry logic"""
        max_retries = ARDUINO_CONNECT_MAX_RETRIES
        retry_delay = ARDUINO_CONNECT_RETRY_DELAY_MS / 1000.0  # Convert to seconds
        
        for attempt in range(max_retries):
            logger.info(f"Attempting to connect to Arduino (attempt {attempt + 1}/{max_retries})")
            
            if self.backend.connect_arduino(port):
                logger.info("Arduino connected successfully")
                self._update_status('arduino_connected', True)
                return True
            else:
                logger.warning(f"Arduino connection failed (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
        
        logger.error("Failed to connect to Arduino after all attempts")
        return False
    
    def start_session(self, user_id: str = "default_user", 
                     club_id: str = "driver", 
                     club_length: float = 1.07, 
                     club_mass: float = 0.205) -> bool:
        """Start a golf session"""
        try:
            if self.backend.start_session(user_id, club_id, club_length, club_mass):
                logger.info(f"Session started: user={user_id}, club={club_id}")
                self._update_status('session_active', True)
                return True
            else:
                logger.error("Failed to start session")
                return False
        except Exception as e:
            logger.error(f"Error starting session: {e}")
            return False
    
    def start_monitoring(self) -> bool:
        """Start swing monitoring"""
        try:
            # Send session config to Arduino
            if not self.backend.send_session_config_to_arduino():
                logger.error("Failed to send session config to Arduino")
                return False
            
            # Start monitoring
            if self.backend.start_swing_monitoring():
                logger.info("Swing monitoring started")
                self._update_status('monitoring_active', True)
                return True
            else:
                logger.error("Failed to start swing monitoring")
                return False
        except Exception as e:
            logger.error(f"Error starting monitoring: {e}")
            return False
    
    def continuous_monitoring_thread(self):
        """Thread for continuous swing monitoring"""
        logger.info("Starting continuous monitoring thread...")
        
        try:
            while self.running and self.system_status['monitoring_active']:
                swing_data = self.backend.wait_for_swing_data()
                if swing_data:
                    logger.info(f"Received swing: {swing_data.swing_id}")
                    # Process swing data here if needed
                else:
                    # No swing data, continue waiting
                    time.sleep(0.1)
                    
        except Exception as e:
            logger.error(f"Error in continuous monitoring thread: {e}")
        finally:
            logger.info("Continuous monitoring thread stopped")
    
    def command_processor_thread(self):
        """Thread for processing user commands"""
        logger.info("Starting command processor thread...")
        
        while self.running:
            try:
                # Process any queued commands
                while not self.command_queue.empty():
                    command = self.command_queue.get_nowait()
                    self._process_command(command)
                
                time.sleep(0.1)  # Small delay to prevent busy waiting
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in command processor thread: {e}")
        
        logger.info("Command processor thread stopped")
    
    def _process_command(self, command: Dict[str, Any]):
        """Process a command from the queue"""
        cmd_type = command.get('type')
        
        if cmd_type == 'start_session':
            self.start_session(**command.get('params', {}))
        elif cmd_type == 'start_monitoring':
            self.start_monitoring()
        elif cmd_type == 'stop_monitoring':
            self.backend.stop_swing_monitoring()
            self._update_status('monitoring_active', False)
        elif cmd_type == 'get_status':
            self._print_status()
        elif cmd_type == 'get_summary':
            self._print_summary()
        else:
            logger.warning(f"Unknown command type: {cmd_type}")
    
    def _print_status(self):
        """Print current system status"""
        with self.status_lock:
            status = self.system_status.copy()
        
        print("\n=== GolfIMU System Status ===")
        print(f"Redis Server: {'✅ Running' if status['redis_running'] else '❌ Stopped'}")
        print(f"Arduino: {'✅ Connected' if status['arduino_connected'] else '❌ Disconnected'}")
        print(f"Backend: {'✅ Running' if status['backend_running'] else '❌ Stopped'}")
        print(f"Session: {'✅ Active' if status['session_active'] else '❌ Inactive'}")
        print(f"Monitoring: {'✅ Active' if status['monitoring_active'] else '❌ Inactive'}")
        
        # Get detailed backend status
        try:
            backend_status = self.backend.get_status()
            if backend_status.get('arduino_port'):
                print(f"Arduino Port: {backend_status['arduino_port']}")
            if backend_status.get('session_id'):
                print(f"Session ID: {backend_status['session_id']}")
        except Exception as e:
            logger.error(f"Error getting backend status: {e}")
    
    def _print_summary(self):
        """Print session summary"""
        try:
            summary = self.backend.get_session_summary()
            print("\n=== Session Summary ===")
            for key, value in summary.items():
                print(f"{key}: {value}")
        except Exception as e:
            logger.error(f"Error getting session summary: {e}")
    
    def start(self):
        """Start the complete GolfIMU system"""
        logger.info("Starting GolfIMU system...")
        
        try:
            # 1. Start Redis
            if not self.start_redis():
                logger.error("Failed to start Redis. Exiting.")
                return False
            
            # 2. Initialize backend
            logger.info("Initializing backend...")
            self._update_status('backend_running', True)
            
            # 3. Connect to Arduino
            if not self.connect_arduino():
                logger.warning("Arduino not connected. System will run in backend-only mode.")
            
            # 4. Start a default session
            if not self.start_session():
                logger.warning("Failed to start default session.")
            
            # 5. Start monitoring threads
            self.running = True
            
            # Start continuous monitoring thread
            monitoring_thread = threading.Thread(
                target=self.continuous_monitoring_thread,
                daemon=True
            )
            monitoring_thread.start()
            
            # Start command processor thread
            command_thread = threading.Thread(
                target=self.command_processor_thread,
                daemon=True
            )
            command_thread.start()
            
            logger.info("GolfIMU system started successfully!")
            self._print_status()
            
            # 6. Start interactive command loop
            self._interactive_loop()
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting GolfIMU system: {e}")
            return False
    
    def _interactive_loop(self):
        """Interactive command loop"""
        print("\n=== GolfIMU System Commands ===")
        print("Available commands:")
        print("  status          - Show system status")
        print("  summary         - Show session summary")
        print("  start_monitor   - Start swing monitoring")
        print("  stop_monitor    - Stop swing monitoring")
        print("  recent_swings   - Show recent swings")
        print("  statistics      - Show swing statistics")
        print("  quit            - Exit the system")
        
        while self.running:
            try:
                command = input("\nGolfIMU> ").strip().lower()
                
                if command == 'quit':
                    break
                elif command == 'status':
                    self._print_status()
                elif command == 'summary':
                    self._print_summary()
                elif command == 'start_monitor':
                    self.command_queue.put({'type': 'start_monitoring'})
                elif command == 'stop_monitor':
                    self.command_queue.put({'type': 'stop_monitoring'})
                elif command == 'recent_swings':
                    try:
                        swings = self.backend.get_recent_swings(5)
                        print("\n=== Recent Swings ===")
                        for i, swing in enumerate(swings, 1):
                            print(f"{i}. Swing {swing['swing_id']}")
                            print(f"   Duration: {swing['duration']:.2f}s")
                            print(f"   Impact: {swing['impact_g_force']:.1f}g")
                            print(f"   Data points: {swing['data_points']}")
                    except Exception as e:
                        logger.error(f"Error getting recent swings: {e}")
                elif command == 'statistics':
                    try:
                        stats = self.backend.get_swing_statistics()
                        print("\n=== Swing Statistics ===")
                        for key, value in stats.items():
                            print(f"{key}: {value}")
                    except Exception as e:
                        logger.error(f"Error getting statistics: {e}")
                elif command:
                    print(f"Unknown command: {command}")
                    
            except KeyboardInterrupt:
                break
            except EOFError:
                break
            except Exception as e:
                logger.error(f"Error in interactive loop: {e}")
    
    def stop(self):
        """Stop the complete GolfIMU system"""
        logger.info("Stopping GolfIMU system...")
        
        self.running = False
        
        # Stop backend
        try:
            self.backend.stop()
            self._update_status('backend_running', False)
        except Exception as e:
            logger.error(f"Error stopping backend: {e}")
        
        # Stop Redis
        self.stop_redis()
        
        logger.info("GolfIMU system stopped")


def main():
    """Main entry point"""
    print("🏌️  GolfIMU System Runner")
    print("=" * 50)
    
    # Verify project structure
    if not verify_project_structure(project_root):
        print("Error: Invalid project structure")
        sys.exit(1)
    
    # Create and start the system runner
    runner = GolfIMUSystemRunner()
    
    try:
        success = runner.start()
        if not success:
            print("Failed to start GolfIMU system")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        runner.stop()


if __name__ == "__main__":
    main() 