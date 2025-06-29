"""
Redis manager for GolfIMU backend
"""
import json
import redis
from typing import List, Dict, Any, Optional
from datetime import datetime

from .config import settings
from .models import IMUData, SessionConfig, SwingEvent, ProcessedMetrics, RedisKey, SwingData


class RedisManager:
    """Manages all Redis operations for GolfIMU"""
    
    def __init__(self):
        """Initialize Redis connection"""
        self.redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=True
        )
    
    def store_swing_data(self, swing_data: SwingData, session_config: SessionConfig) -> bool:
        """Store complete swing data in Redis"""
        try:
            # Create Redis key
            redis_key = RedisKey(
                session_id=session_config.session_id,
                user_id=session_config.user_id,
                club_id=session_config.club_id,
                data_type="swings"
            )
            
            # Convert swing data to JSON
            swing_json = json.dumps({
                "swing_id": swing_data.swing_id,
                "session_id": swing_data.session_id,
                "imu_data_points": [
                    {
                        "ax": point.ax, "ay": point.ay, "az": point.az,
                        "gx": point.gx, "gy": point.gy, "gz": point.gz,
                        "mx": point.mx, "my": point.my, "mz": point.mz,
                        "timestamp": point.timestamp.isoformat()
                    }
                    for point in swing_data.imu_data_points
                ],
                "swing_start_time": swing_data.swing_start_time.isoformat(),
                "swing_end_time": swing_data.swing_end_time.isoformat(),
                "swing_duration": swing_data.swing_duration,
                "impact_g_force": swing_data.impact_g_force,
                "swing_type": swing_data.swing_type
            })
            
            # Store swing data
            self.redis_client.lpush(redis_key.to_key(), swing_json)
            
            return True
            
        except Exception as e:
            print(f"Error storing swing data: {e}")
            return False
    
    def get_swing_data(self, session_config: SessionConfig, count: Optional[int] = None) -> List[SwingData]:
        """Get swing data from Redis"""
        try:
            redis_key = RedisKey(
                session_id=session_config.session_id,
                user_id=session_config.user_id,
                club_id=session_config.club_id,
                data_type="swings"
            )
            
            # Get swing data from Redis
            if count is None:
                count = 100  # Default to last 100 swings
            
            data_list = self.redis_client.lrange(redis_key.to_key(), 0, count - 1)
            
            # Parse JSON data back to SwingData objects
            swing_data_list = []
            for data_json in reversed(data_list):  # Reverse to get chronological order
                data_dict = json.loads(data_json)
                
                # Parse IMU data points
                imu_data_points = []
                for imu_dict in data_dict["imu_data_points"]:
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
                        timestamp=datetime.fromisoformat(imu_dict["timestamp"])
                    )
                    imu_data_points.append(imu_data)
                
                swing_data = SwingData(
                    swing_id=data_dict["swing_id"],
                    session_id=data_dict["session_id"],
                    imu_data_points=imu_data_points,
                    swing_start_time=datetime.fromisoformat(data_dict["swing_start_time"]),
                    swing_end_time=datetime.fromisoformat(data_dict["swing_end_time"]),
                    swing_duration=data_dict["swing_duration"],
                    impact_g_force=data_dict["impact_g_force"],
                    swing_type=data_dict["swing_type"]
                )
                swing_data_list.append(swing_data)
            
            return swing_data_list
            
        except Exception as e:
            print(f"Error getting swing data: {e}")
            return []
    
    def store_swing_event(self, event: SwingEvent) -> bool:
        """Store swing event in Redis"""
        try:
            redis_key = RedisKey(
                session_id=event.session_id,
                user_id="",  # Will be filled from session config
                club_id="",  # Will be filled from session config
                data_type="events"
            )
            
            event_json = json.dumps({
                "swing_id": event.swing_id,
                "event_type": event.event_type,
                "timestamp": event.timestamp.isoformat(),
                "data": event.data
            })
            
            self.redis_client.lpush(redis_key.to_key(), event_json)
            return True
            
        except Exception as e:
            print(f"Error storing swing event: {e}")
            return False
    
    def store_session_config(self, session_config: SessionConfig) -> bool:
        """Store session configuration in Redis"""
        try:
            redis_key = f"session_config:{session_config.session_id}"
            
            config_json = json.dumps({
                "session_id": session_config.session_id,
                "user_id": session_config.user_id,
                "club_id": session_config.club_id,
                "club_length": session_config.club_length,
                "club_mass": session_config.club_mass,
                "face_normal_calibration": session_config.face_normal_calibration,
                "impact_threshold": session_config.impact_threshold,
                "session_start_time": session_config.session_start_time.isoformat()
            })
            
            self.redis_client.set(redis_key, config_json)
            return True
            
        except Exception as e:
            print(f"Error storing session config: {e}")
            return False
    
    def get_session_config(self, session_id: str) -> Optional[SessionConfig]:
        """Get session configuration from Redis"""
        try:
            redis_key = f"session_config:{session_id}"
            config_json = self.redis_client.get(redis_key)
            
            if config_json:
                config_dict = json.loads(config_json)
                return SessionConfig(
                    session_id=config_dict["session_id"],
                    user_id=config_dict["user_id"],
                    club_id=config_dict["club_id"],
                    club_length=config_dict["club_length"],
                    club_mass=config_dict["club_mass"],
                    face_normal_calibration=config_dict["face_normal_calibration"],
                    impact_threshold=config_dict["impact_threshold"],
                    session_start_time=datetime.fromisoformat(config_dict["session_start_time"])
                )
            
            return None
            
        except Exception as e:
            print(f"Error getting session config: {e}")
            return None
    
    def clear_session_data(self, session_id: str) -> bool:
        """Clear all data for a session"""
        try:
            # Get session config to find user_id and club_id
            session_config = self.get_session_config(session_id)
            if not session_config:
                return False
            
            # Clear swing data
            swings_key = RedisKey(
                session_id=session_id,
                user_id=session_config.user_id,
                club_id=session_config.club_id,
                data_type="swings"
            )
            self.redis_client.delete(swings_key.to_key())
            
            # Clear events
            events_key = RedisKey(
                session_id=session_id,
                user_id=session_config.user_id,
                club_id=session_config.club_id,
                data_type="events"
            )
            self.redis_client.delete(events_key.to_key())
            
            # Clear session config
            config_key = f"session_config:{session_id}"
            self.redis_client.delete(config_key)
            
            return True
            
        except Exception as e:
            print(f"Error clearing session data: {e}")
            return False
    
    def get_session_swing_count(self, session_config: SessionConfig) -> int:
        """Get the number of swings in a session"""
        try:
            redis_key = RedisKey(
                session_id=session_config.session_id,
                user_id=session_config.user_id,
                club_id=session_config.club_id,
                data_type="swings"
            )
            
            return self.redis_client.llen(redis_key.to_key())
            
        except Exception as e:
            print(f"Error getting swing count: {e}")
            return 0

    def store_imu_data(self, imu_data: IMUData, session_config: SessionConfig) -> bool:
        """Store IMU data in Redis buffer"""
        try:
            redis_key = RedisKey(
                session_id=session_config.session_id,
                user_id=session_config.user_id,
                club_id=session_config.club_id,
                data_type="imu_buffer"
            )
            
            # Convert IMU data to JSON
            imu_json = json.dumps({
                "ax": imu_data.ax,
                "ay": imu_data.ay,
                "az": imu_data.az,
                "gx": imu_data.gx,
                "gy": imu_data.gy,
                "gz": imu_data.gz,
                "mx": imu_data.mx,
                "my": imu_data.my,
                "mz": imu_data.mz,
                "timestamp": imu_data.timestamp.isoformat()
            })
            
            # Store IMU data in buffer (limit buffer size to prevent memory issues)
            self.redis_client.lpush(redis_key.to_key(), imu_json)
            
            # Keep only last 1000 data points
            self.redis_client.ltrim(redis_key.to_key(), 0, 999)
            
            return True
            
        except Exception as e:
            print(f"Error storing IMU data: {e}")
            return False

    def get_imu_buffer(self, session_config: SessionConfig, count: Optional[int] = None) -> List[IMUData]:
        """Get IMU data buffer from Redis"""
        try:
            redis_key = RedisKey(
                session_id=session_config.session_id,
                user_id=session_config.user_id,
                club_id=session_config.club_id,
                data_type="imu_buffer"
            )
            
            # Get IMU data from Redis
            if count is None:
                count = 100  # Default to last 100 data points
            
            data_list = self.redis_client.lrange(redis_key.to_key(), 0, count - 1)
            
            # Parse JSON data back to IMUData objects
            imu_data_list = []
            for data_json in reversed(data_list):  # Reverse to get chronological order
                try:
                    data_dict = json.loads(data_json)
                    imu_data = IMUData(
                        ax=data_dict["ax"],
                        ay=data_dict["ay"],
                        az=data_dict["az"],
                        gx=data_dict["gx"],
                        gy=data_dict["gy"],
                        gz=data_dict["gz"],
                        mx=data_dict["mx"],
                        my=data_dict["my"],
                        mz=data_dict["mz"],
                        timestamp=datetime.fromisoformat(data_dict["timestamp"])
                    )
                    imu_data_list.append(imu_data)
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    print(f"Error parsing IMU data: {e}")
                    continue
            
            return imu_data_list
            
        except Exception as e:
            print(f"Error getting IMU buffer: {e}")
            return [] 