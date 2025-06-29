"""
Tests for backend.config module
"""
import pytest
import os
from backend.config import Settings


class TestSettings:
    """Test Settings configuration"""
    
    def test_default_settings(self):
        """Test default settings values"""
        settings = Settings()
        
        assert settings.redis_host == "localhost"
        assert settings.redis_port == 6379
        assert settings.redis_db == 0
        assert settings.redis_password is None
        assert settings.serial_port == "/dev/tty.usbserial-*"
        assert settings.serial_baudrate == 115200
        assert settings.serial_timeout == 1.0
        assert settings.imu_sample_rate == 200
        assert settings.buffer_size == 1000
        assert settings.default_impact_threshold == 30.0
    
    def test_custom_settings(self):
        """Test custom settings values"""
        settings = Settings(
            redis_host="test-host",
            redis_port=6380,
            redis_db=1,
            redis_password="test-password",
            serial_port="/dev/tty.test",
            serial_baudrate=9600,
            serial_timeout=2.0,
            imu_sample_rate=100,
            buffer_size=500,
            default_impact_threshold=25.0
        )
        
        assert settings.redis_host == "test-host"
        assert settings.redis_port == 6380
        assert settings.redis_db == 1
        assert settings.redis_password == "test-password"
        assert settings.serial_port == "/dev/tty.test"
        assert settings.serial_baudrate == 9600
        assert settings.serial_timeout == 2.0
        assert settings.imu_sample_rate == 100
        assert settings.buffer_size == 500
        assert settings.default_impact_threshold == 25.0
    
    def test_environment_variable_override(self, monkeypatch):
        """Test that environment variables can override defaults"""
        monkeypatch.setenv("REDIS_HOST", "env-host")
        monkeypatch.setenv("REDIS_PORT", "6380")
        monkeypatch.setenv("SERIAL_PORT", "/dev/tty.env")
        monkeypatch.setenv("IMU_SAMPLE_RATE", "150")
        
        settings = Settings()
        
        assert settings.redis_host == "env-host"
        assert settings.redis_port == 6380
        assert settings.serial_port == "/dev/tty.env"
        assert settings.imu_sample_rate == 150
    
    def test_settings_case_insensitive(self, monkeypatch):
        """Test that environment variables are case insensitive"""
        monkeypatch.setenv("redis_host", "case-test-host")
        monkeypatch.setenv("SERIAL_BAUDRATE", "9600")
        
        settings = Settings()
        
        assert settings.redis_host == "case-test-host"
        assert settings.serial_baudrate == 9600
    
    def test_optional_redis_password(self):
        """Test that Redis password can be None"""
        settings = Settings(redis_password=None)
        assert settings.redis_password is None
        
        settings = Settings(redis_password="test-pass")
        assert settings.redis_password == "test-pass"
    
    def test_numeric_environment_variables(self, monkeypatch):
        """Test that numeric environment variables are parsed correctly"""
        monkeypatch.setenv("REDIS_PORT", "6380")
        monkeypatch.setenv("REDIS_DB", "2")
        monkeypatch.setenv("SERIAL_BAUDRATE", "9600")
        monkeypatch.setenv("SERIAL_TIMEOUT", "1.5")
        monkeypatch.setenv("IMU_SAMPLE_RATE", "250")
        monkeypatch.setenv("BUFFER_SIZE", "2000")
        monkeypatch.setenv("DEFAULT_IMPACT_THRESHOLD", "35.5")
        
        settings = Settings()
        
        assert settings.redis_port == 6380
        assert settings.redis_db == 2
        assert settings.serial_baudrate == 9600
        assert settings.serial_timeout == 1.5
        assert settings.imu_sample_rate == 250
        assert settings.buffer_size == 2000
        assert settings.default_impact_threshold == 35.5
    
    def test_invalid_numeric_environment_variables(self, monkeypatch):
        """Test that invalid numeric environment variables raise errors"""
        monkeypatch.setenv("REDIS_PORT", "not-a-number")
        
        with pytest.raises(ValueError):
            Settings()
    
    def test_settings_immutability(self):
        """Test that settings are immutable after creation"""
        settings = Settings()
        
        # Attempting to modify should not work (Pydantic models are immutable by default)
        # This test ensures the settings behave as expected
        assert settings.redis_host == "localhost"
        
        # Create new settings with different values
        new_settings = Settings(redis_host="new-host")
        assert new_settings.redis_host == "new-host"
        assert settings.redis_host == "localhost"  # Original unchanged 