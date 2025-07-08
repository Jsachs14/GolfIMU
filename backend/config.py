"""
Configuration settings for GolfIMU backend
"""
import os
import sys
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Add project root to path to import global_config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from global_config import *


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Redis Configuration
    redis_host: str = REDIS_HOST
    redis_port: int = REDIS_PORT
    redis_db: int = REDIS_DB
    redis_password: Optional[str] = REDIS_PASSWORD
    
    # Serial Configuration
    serial_port: str = SERIAL_PORT_PATTERN
    serial_baudrate: int = SERIAL_BAUDRATE
    serial_timeout: float = SERIAL_TIMEOUT
    
    # Data Processing
    imu_sample_rate: int = IMU_SAMPLE_RATE_HZ
    buffer_size: int = IMU_BUFFER_SIZE
    
    # Session Management
    default_impact_threshold: float = DEFAULT_IMPACT_THRESHOLD_G
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False
    )


# Global settings instance
settings = Settings() 