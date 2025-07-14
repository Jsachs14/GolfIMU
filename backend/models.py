"""
Data models for GolfIMU backend
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid


class IMUData(BaseModel):
    """Raw IMU sensor data"""
    ax: float = Field(..., description="Accelerometer X (m/s²)")
    ay: float = Field(..., description="Accelerometer Y (m/s²)")
    az: float = Field(..., description="Accelerometer Z (m/s²)")
    gx: float = Field(..., description="Gyroscope X (rad/s)")
    gy: float = Field(..., description="Gyroscope Y (rad/s)")
    gz: float = Field(..., description="Gyroscope Z (rad/s)")
    mx: float = Field(..., description="Magnetometer X (μT)")
    my: float = Field(..., description="Magnetometer Y (μT)")
    mz: float = Field(..., description="Magnetometer Z (μT)")
    qw: float = Field(..., description="Quaternion W component")
    qx: float = Field(..., description="Quaternion X component")
    qy: float = Field(..., description="Quaternion Y component")
    qz: float = Field(..., description="Quaternion Z component")
    timestamp: datetime = Field(default_factory=datetime.now)


class SwingData(BaseModel):
    """Complete swing data with all IMU readings"""
    swing_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = Field(..., description="Session identifier")
    imu_data_points: List[IMUData] = Field(..., description="All IMU readings for the swing")
    swing_start_time: datetime = Field(..., description="Start of swing")
    swing_end_time: datetime = Field(..., description="End of swing (impact)")
    swing_duration: float = Field(..., description="Swing duration in seconds")
    impact_g_force: float = Field(..., description="Peak g-force at impact")
    swing_type: str = Field(default="full_swing", description="Type of swing (full_swing, chip, putt, etc.)")


class SessionConfig(BaseModel):
    """Session configuration and metadata"""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="User identifier")
    club_id: str = Field(..., description="Club identifier (driver, iron, etc.)")
    club_length: float = Field(..., description="Club length in meters")
    club_mass: float = Field(..., description="Club mass in kg")
    face_normal_calibration: Optional[List[float]] = Field(None, description="Face normal vector [x, y, z]")
    impact_threshold: float = Field(default=30.0, description="Impact detection threshold in g")
    session_start_time: datetime = Field(default_factory=datetime.now)


class SwingEvent(BaseModel):
    """Swing event data"""
    swing_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    event_type: str = Field(..., description="Type of swing event (start, top, impact, etc.)")
    timestamp: datetime = Field(default_factory=datetime.now)
    data: Optional[Dict[str, Any]] = Field(None, description="Additional event data")


class ProcessedMetrics(BaseModel):
    """Processed swing metrics (placeholder for future analyzer functions)"""
    swing_id: str
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Calculated metrics")


class RedisKey(BaseModel):
    """Redis key structure helper"""
    session_id: str
    user_id: str
    club_id: str
    data_type: str  # "swings", "events", "metrics", etc.
    
    def to_key(self) -> str:
        """Convert to Redis key format"""
        return f"session:{self.session_id}:user:{self.user_id}:club:{self.club_id}:{self.data_type}" 