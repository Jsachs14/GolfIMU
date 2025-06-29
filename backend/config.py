"""
Configuration settings for GolfIMU backend
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # Serial Configuration
    serial_port: str = "/dev/tty.usbserial-*"  # Default for Mac
    serial_baudrate: int = 115200
    serial_timeout: float = 1.0
    
    # Data Processing
    imu_sample_rate: int = 200  # Hz
    buffer_size: int = 1000  # Number of samples to keep in ring buffer
    
    # Session Management
    default_impact_threshold: float = 30.0  # g-force threshold for impact detection
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False
    )


# Global settings instance
settings = Settings() 