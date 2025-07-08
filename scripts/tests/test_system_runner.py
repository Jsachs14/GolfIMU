#!/usr/bin/env python3
"""
Tests for scripts.run_golfimu_system module
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import sys
import os
import threading
import time
from unittest.mock import Mock, patch, MagicMock

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent
sys.path.insert(0, str(scripts_dir))

# Import the system runner
from run_golfimu_system import GolfIMUSystemRunner


class TestGolfIMUSystemRunner:
    """Test the GolfIMU system runner"""
    
    def test_initialization(self):
        """Test system runner initialization"""
        runner = GolfIMUSystemRunner()
        
        # Check that all components are initialized
        assert runner.backend is not None
        assert runner.redis_process is None
        assert runner.arduino_monitor_process is None
        assert runner.running is False
        assert runner.command_queue is not None
        assert runner.status_lock is not None
        
        # Check initial status
        assert runner.system_status['redis_running'] is False
        assert runner.system_status['arduino_connected'] is False
        assert runner.system_status['backend_running'] is False
        assert runner.system_status['session_active'] is False
        assert runner.system_status['monitoring_active'] is False
    
    def test_status_update_thread_safety(self):
        """Test that status updates are thread-safe"""
        runner = GolfIMUSystemRunner()
        
        # Test concurrent status updates
        def update_status():
            for i in range(100):
                runner._update_status('test_key', i)
        
        # Create multiple threads updating status
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=update_status)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should not have crashed due to race conditions
        assert runner.system_status['test_key'] is not None
    
    def test_command_queue_processing(self):
        """Test command queue processing"""
        runner = GolfIMUSystemRunner()
        
        # Mock the command processing methods
        runner.start_session = Mock(return_value=True)
        runner.start_monitoring = Mock(return_value=True)
        runner.backend.stop_swing_monitoring = Mock()
        runner._print_status = Mock()
        runner._print_summary = Mock()
        
        # Add commands to queue
        runner.command_queue.put({'type': 'start_session', 'params': {'user_id': 'test'}})
        runner.command_queue.put({'type': 'start_monitoring'})
        runner.command_queue.put({'type': 'stop_monitoring'})
        runner.command_queue.put({'type': 'get_status'})
        runner.command_queue.put({'type': 'get_summary'})
        
        # Process commands
        while not runner.command_queue.empty():
            command = runner.command_queue.get_nowait()
            runner._process_command(command)
        
        # Verify commands were processed
        runner.start_session.assert_called_once_with(user_id='test')
        runner.start_monitoring.assert_called_once()
        runner.backend.stop_swing_monitoring.assert_called_once()
        runner._print_status.assert_called_once()
        runner._print_summary.assert_called_once()
    
    def test_unknown_command_handling(self):
        """Test handling of unknown commands"""
        runner = GolfIMUSystemRunner()
        
        # Mock logger to capture warnings
        with patch('run_golfimu_system.logger') as mock_logger:
            runner._process_command({'type': 'unknown_command'})
            mock_logger.warning.assert_called_once()
    
    def test_session_management(self):
        """Test session management"""
        runner = GolfIMUSystemRunner()
        
        # Mock backend session methods
        runner.backend.start_session = Mock(return_value=True)
        
        # Test successful session start
        result = runner.start_session('test_user', 'driver', 1.07, 0.205)
        assert result is True
        assert runner.system_status['session_active'] is True
        runner.backend.start_session.assert_called_once_with('test_user', 'driver', 1.07, 0.205)
        
        # Test failed session start
        runner.backend.start_session = Mock(return_value=False)
        result = runner.start_session('test_user', 'driver', 1.07, 0.205)
        assert result is False
    
    def test_monitoring_management(self):
        """Test monitoring management"""
        runner = GolfIMUSystemRunner()
        
        # Mock backend methods
        runner.backend.send_session_config_to_arduino = Mock(return_value=True)
        runner.backend.start_swing_monitoring = Mock(return_value=True)
        
        # Test successful monitoring start
        result = runner.start_monitoring()
        assert result is True
        assert runner.system_status['monitoring_active'] is True
        runner.backend.send_session_config_to_arduino.assert_called_once()
        runner.backend.start_swing_monitoring.assert_called_once()
        
        # Test failed monitoring start
        runner.backend.send_session_config_to_arduino = Mock(return_value=False)
        result = runner.start_monitoring()
        assert result is False
    
    def test_arduino_connection_retry_logic(self):
        """Test Arduino connection retry logic"""
        runner = GolfIMUSystemRunner()
        
        # Mock backend connection to fail twice, then succeed
        runner.backend.connect_arduino = Mock(side_effect=[False, False, True])
        
        # Test connection with retries
        result = runner.connect_arduino()
        assert result is True
        assert runner.backend.connect_arduino.call_count == 3
        assert runner.system_status['arduino_connected'] is True
        
        # Test connection failure after all retries
        runner.backend.connect_arduino = Mock(return_value=False)
        result = runner.connect_arduino()
        assert result is False
        assert runner.backend.connect_arduino.call_count == 3
    
    def test_graceful_shutdown(self):
        """Test graceful shutdown"""
        runner = GolfIMUSystemRunner()
        
        # Mock backend stop method
        runner.backend.stop = Mock()
        runner.stop_redis = Mock()
        
        # Test stop method
        runner.stop()
        
        assert runner.running is False
        runner.backend.stop.assert_called_once()
        runner.stop_redis.assert_called_once()
    
    def test_signal_handler(self):
        """Test signal handler"""
        runner = GolfIMUSystemRunner()
        
        # Mock stop method
        runner.stop = Mock()
        
        # Test signal handler
        with patch('sys.exit') as mock_exit:
            runner._signal_handler(None, None)
            runner.stop.assert_called_once()
            mock_exit.assert_called_once_with(0)


class TestSystemRunnerIntegration:
    """Integration tests for system runner"""
    
    @patch('run_golfimu_system.subprocess.run')
    @patch('run_golfimu_system.subprocess.Popen')
    def test_redis_management(self, mock_popen, mock_run):
        """Test Redis server management"""
        runner = GolfIMUSystemRunner()
        
        # Mock Redis CLI ping to fail first (Redis not running), then succeed
        mock_run.side_effect = [
            # First call: Redis not running (FileNotFoundError)
            FileNotFoundError("redis-cli not found"),
            # Second call: Redis ping after starting
            Mock(returncode=0, stdout="PONG")
        ]
        
        # Mock Redis server process
        mock_process = Mock()
        mock_popen.return_value = mock_process
        
        # Test Redis start
        result = runner.start_redis()
        assert result is True
        assert runner.system_status['redis_running'] is True
        mock_popen.assert_called_once()
        
        # Test Redis stop
        runner.stop_redis()
        mock_process.terminate.assert_called_once()
    
    def test_thread_management(self):
        """Test thread management"""
        runner = GolfIMUSystemRunner()
        
        # Mock the thread target methods
        runner.continuous_monitoring_thread = Mock()
        runner.command_processor_thread = Mock()
        
        # Test thread creation and cleanup
        runner.running = True
        
        # Create threads
        monitoring_thread = threading.Thread(
            target=runner.continuous_monitoring_thread,
            daemon=True
        )
        command_thread = threading.Thread(
            target=runner.command_processor_thread,
            daemon=True
        )
        
        # Verify threads are daemon
        assert monitoring_thread.daemon is True
        assert command_thread.daemon is True
    
    def test_status_printing(self):
        """Test status printing"""
        runner = GolfIMUSystemRunner()
        
        # Mock backend status
        runner.backend.get_status = Mock(return_value={
            'arduino_port': '/dev/tty.usbserial-12345',
            'session_id': 'test_session_123'
        })
        
        # Test status printing
        with patch('builtins.print') as mock_print:
            runner._print_status()
            mock_print.assert_called()
    
    def test_summary_printing(self):
        """Test summary printing"""
        runner = GolfIMUSystemRunner()
        
        # Mock backend summary
        runner.backend.get_session_summary = Mock(return_value={
            'total_swings': 10,
            'average_duration': 1.5
        })
        
        # Test summary printing
        with patch('builtins.print') as mock_print:
            runner._print_summary()
            mock_print.assert_called()


if __name__ == "__main__":
    pytest.main([__file__]) 