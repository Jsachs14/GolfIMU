"""
Redis manager for GolfIMU backend - High Performance Version
"""
import json
import redis
import os
import pickle
import threading
from typing import List, Dict, Any, Optional
from datetime import datetime

from .config import settings
from .models import IMUData, SessionConfig, SwingEvent, ProcessedMetrics, RedisKey, SwingData

# Import performance constants
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from global_config import IMU_TRIM_INTERVAL, IMU_MAX_BUFFER_SIZE


class RedisManager:
    """Manages all Redis operations for GolfIMU with high-performance disk storage"""
    
    def __init__(self):
        """Initialize Redis connection"""
        self.redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=True
        )
        
        # Performance optimization: track operations to reduce trimming frequency
        self._imu_operation_count = 0
        
        # Disk storage optimization
        self.data_dir = "./data"
        self._session_id = None
        self._current_file_path = None
        self._imu_buffer = []
        self._buffer_lock = threading.Lock()
        
    def _get_imu_file_path(self, session_id: str) -> str:
        """Get file path for IMU data"""
        return os.path.join(self.data_dir, f"imu_{session_id}.jsonl")
    
    def _write_imu_batch_simple(self, batch_data):
        """Write IMU batch to disk with simple, reliable approach"""
        try:
            with open(self._current_file_path, 'a') as f:
                for imu_dict in batch_data:
                    f.write(json.dumps(imu_dict) + '\n')
        except Exception as e:
            print(f"Error writing IMU data to disk: {e}")
    
    def _write_imu_batch(self, batch_data):
        """Write IMU batch to disk with optimized buffering"""
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self._current_file_path), exist_ok=True)
            
            # Use buffered writes for better performance
            with open(self._current_file_path, 'a', buffering=8192) as f:
                for imu_dict in batch_data:
                    f.write(json.dumps(imu_dict) + '\n')
                    
        except Exception as e:
            print(f"Error writing IMU data to disk: {e}")
    
    def store_imu_data(self, imu_data: IMUData, session_config: SessionConfig) -> bool:
        """Store IMU data with simple 200 Hz approach for consistent performance
        
        Args:
            imu_data: IMU data to store
            session_config: Current session configuration
            
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            # Initialize if new session
            if self._session_id != session_config.session_id:
                self._session_id = session_config.session_id
                self._imu_buffer = []
                
                # Create Redis counter for this session
                counter_key = f"imu_counter:{session_config.session_id}"
                self.redis_client.set(counter_key, 0)
            
            # Ultra-simple dict storage - minimal overhead
            imu_dict = {
                "t": imu_data.timestamp.isoformat() if hasattr(imu_data.timestamp, 'isoformat') else str(imu_data.timestamp),
                "ax": imu_data.ax, "ay": imu_data.ay, "az": imu_data.az,
                "gx": imu_data.gx, "gy": imu_data.gy, "gz": imu_data.gz,
                "mx": imu_data.mx, "my": imu_data.my, "mz": imu_data.mz,
                "qw": imu_data.qw, "qx": imu_data.qx, "qy": imu_data.qy, "qz": imu_data.qz
            }
            
            # Just append to list - simple and fast
            self._imu_buffer.append(imu_dict)
            
            # Update Redis counter every 1000 samples (infrequent)
            self._imu_operation_count += 1
            if self._imu_operation_count >= 1000:
                counter_key = f"imu_counter:{session_config.session_id}"
                self.redis_client.incrby(counter_key, 1000)
                self._imu_operation_count = 0
            
            return True
            
        except Exception as e:
            print(f"Error storing IMU data: {e}")
            return False
    
    def get_imu_buffer(self, session_config: SessionConfig, count: Optional[int] = None) -> List[IMUData]:
        """Get IMU data from disk storage"""
        try:
            file_path = self._get_imu_file_path(session_config.session_id)
            if not os.path.exists(file_path):
                return []
            
            imu_data_list = []
            with open(file_path, 'r') as f:
                for line in f:
                    if count and len(imu_data_list) >= count:
                        break
                    
                    try:
                        data = json.loads(line.strip())
                        # Parse timestamp back to datetime
                        timestamp_str = data['t']
                        if isinstance(timestamp_str, str):
                            # Try to parse ISO format first
                            try:
                                timestamp = datetime.fromisoformat(timestamp_str)
                            except ValueError:
                                # Fallback to parsing as float
                                timestamp = datetime.fromtimestamp(float(timestamp_str))
                        else:
                            timestamp = timestamp_str
                            
                        imu_data = IMUData(
                            timestamp=timestamp,
                            ax=data['ax'], ay=data['ay'], az=data['az'],
                            gx=data['gx'], gy=data['gy'], gz=data['gz'],
                            mx=data['mx'], my=data['my'], mz=data['mz'],
                            qw=data['qw'], qx=data['qx'], qy=data['qy'], qz=data['qz']
                        )
                        imu_data_list.append(imu_data)
                    except Exception as e:
                        print(f"Error parsing IMU data line: {e}")
                        continue
            
            return imu_data_list
            
        except Exception as e:
            print(f"Error getting IMU buffer: {e}")
            return []
    
    def store_swing_data(self, swing_data: SwingData, session_config: SessionConfig) -> bool:
        """Store complete swing data in Redis"""
        try:
            # Create Redis key
            redis_key = RedisKey(
                session_id=session_config.session_id,
                user_id=session_config.user_id,
                club_id=session_config.club_id,
                data_type="swing_data"
            )
            
            # Convert to JSON
            swing_json = json.dumps({
                "swing_id": swing_data.swing_id,
                "timestamp": swing_data.timestamp.isoformat(),
                "duration": swing_data.duration,
                "peak_velocity": swing_data.peak_velocity,
                "impact_velocity": swing_data.impact_velocity,
                "backswing_time": swing_data.backswing_time,
                "downswing_time": swing_data.downswing_time,
                "follow_through_time": swing_data.follow_through_time,
                "metrics": swing_data.metrics.dict() if swing_data.metrics else None
            })
            
            # Store in Redis
            self.redis_client.lpush(redis_key.to_string(), swing_json)
            
            # Keep only last 100 swings
            self.redis_client.ltrim(redis_key.to_string(), 0, 99)
            
            return True
            
        except Exception as e:
            print(f"Error storing swing data: {e}")
            return False
    
    def store_swing_event(self, event: SwingEvent, session_config: SessionConfig) -> bool:
        """Store swing event in Redis"""
        try:
            redis_key = RedisKey(
                session_id=session_config.session_id,
                user_id=session_config.user_id,
                club_id=session_config.club_id,
                data_type="swing_events"
            )
            
            event_json = json.dumps({
                "event_type": event.event_type,
                "timestamp": event.timestamp.isoformat(),
                "velocity": event.velocity,
                "acceleration": event.acceleration,
                "g_force": event.g_force
            })
            
            self.redis_client.lpush(redis_key.to_string(), event_json)
            self.redis_client.ltrim(redis_key.to_string(), 0, 999)
            
            return True
            
        except Exception as e:
            print(f"Error storing swing event: {e}")
            return False
    
    def get_recent_swings(self, session_config: SessionConfig, count: int = 10) -> List[SwingData]:
        """Get recent swing data from Redis"""
        try:
            redis_key = RedisKey(
                session_id=session_config.session_id,
                user_id=session_config.user_id,
                club_id=session_config.club_id,
                data_type="swing_data"
            )
            
            swing_data_list = []
            swing_jsons = self.redis_client.lrange(redis_key.to_string(), 0, count - 1)
            
            for swing_json in swing_jsons:
                try:
                    data = json.loads(swing_json)
                    swing_data = SwingData(
                        swing_id=data["swing_id"],
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                        duration=data["duration"],
                        peak_velocity=data["peak_velocity"],
                        impact_velocity=data["impact_velocity"],
                        backswing_time=data["backswing_time"],
                        downswing_time=data["downswing_time"],
                        follow_through_time=data["follow_through_time"],
                        metrics=ProcessedMetrics(**data["metrics"]) if data["metrics"] else None
                    )
                    swing_data_list.append(swing_data)
                except Exception as e:
                    print(f"Error parsing swing data: {e}")
                    continue
            
            return swing_data_list
            
        except Exception as e:
            print(f"Error getting recent swings: {e}")
            return []
    
    def get_session_statistics(self, session_config: SessionConfig) -> Dict[str, Any]:
        """Get session statistics"""
        try:
            # Get IMU data count from Redis counter
            counter_key = f"imu_counter:{session_config.session_id}"
            imu_count = int(self.redis_client.get(counter_key) or 0)
            
            # Get swing count
            redis_key = RedisKey(
                session_id=session_config.session_id,
                user_id=session_config.user_id,
                club_id=session_config.club_id,
                data_type="swing_data"
            )
            swing_count = self.redis_client.llen(redis_key.to_string())
            
            return {
                "session_id": session_config.session_id,
                "user_id": session_config.user_id,
                "club_id": session_config.club_id,
                "imu_data_points": imu_count,
                "swing_count": swing_count,
                "data_file_size": self._get_file_size(session_config.session_id)
            }
            
        except Exception as e:
            print(f"Error getting session statistics: {e}")
            return {}
    
    def _get_file_size(self, session_id: str) -> int:
        """Get size of IMU data file in bytes"""
        try:
            file_path = self._get_imu_file_path(session_id)
            if os.path.exists(file_path):
                return os.path.getsize(file_path)
            return 0
        except Exception:
            return 0
    
    def cleanup_session(self, session_config: SessionConfig):
        """Clean up session data"""
        try:
            # Save any remaining data
            if self._imu_buffer:
                self.save_session_data(session_config)
                self._imu_buffer = []
            
            # Clear Redis counters
            counter_key = f"imu_counter:{session_config.session_id}"
            self.redis_client.delete(counter_key)
            
        except Exception as e:
            print(f"Error cleaning up session: {e}")
    
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

    def save_session_data(self, session_config: SessionConfig) -> bool:
        """Save all collected IMU data to disk when session ends"""
        try:
            if not self._imu_buffer:
                return True
                
            # Create file path
            file_path = self._get_imu_file_path(session_config.session_id)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Write all data to disk at once
            with open(file_path, 'w') as f:
                for imu_dict in self._imu_buffer:
                    f.write(json.dumps(imu_dict) + '\n')
            
            print(f"Saved {len(self._imu_buffer)} IMU data points to {file_path}")
            return True
            
        except Exception as e:
            print(f"Error saving session data: {e}")
            return False 