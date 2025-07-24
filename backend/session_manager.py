"""
Session manager for GolfIMU backend
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

from .models import SessionConfig, SwingEvent, SwingData
from .redis_manager import RedisManager


class SessionManager:
    """Manages user sessions and club configurations"""
    
    def __init__(self, redis_manager: RedisManager):
        """Initialize session manager"""
        self.redis_manager = redis_manager
        self.current_session: Optional[SessionConfig] = None
    
    def create_session(self, 
                      user_id: str,
                      club_id: str,
                      club_length: float,
                      club_mass: float,
                      face_normal_calibration: Optional[list] = None,
                      impact_threshold: Optional[float] = None) -> SessionConfig:
        """Create a new session with user and club configuration"""
        
        session_config = SessionConfig(
            user_id=user_id,
            club_id=club_id,
            club_length=club_length,
            club_mass=club_mass,
            face_normal_calibration=face_normal_calibration,
            impact_threshold=impact_threshold or 30.0
        )
        
        # Store session config in Redis
        if self.redis_manager.store_session_config(session_config):
            self.current_session = session_config
            print(f"Created session {session_config.session_id} for user {user_id} with club {club_id}")
            return session_config
        else:
            raise Exception("Failed to create session")
    
    def load_session(self, session_id: str) -> Optional[SessionConfig]:
        """Load an existing session"""
        session_config = self.redis_manager.get_session_config(session_id)
        if session_config:
            self.current_session = session_config
            print(f"Loaded session {session_id}")
            return session_config
        else:
            print(f"Session {session_id} not found")
            return None
    
    def end_session(self) -> bool:
        """End current session"""
        if self.current_session:
            # Could add session end time and summary here
            print(f"Ended session {self.current_session.session_id}")
            self.current_session = None
            return True
        return False
    
    def clear_session_data(self, session_id: str) -> bool:
        """Clear all data for a session"""
        success = self.redis_manager.clear_session_data(session_id)
        if success:
            print(f"Cleared data for session {session_id}")
        return success
    
    def get_current_session(self) -> Optional[SessionConfig]:
        """Get current session configuration"""
        return self.current_session
    
    def store_swing_data(self, swing_data: SwingData) -> bool:
        """Store complete swing data for current session"""
        if not self.current_session:
            print("No active session")
            return False
        
        # Ensure swing data belongs to current session
        swing_data.session_id = self.current_session.session_id
        
        success = self.redis_manager.store_swing_data(swing_data, self.current_session)
        if success:
            print(f"Stored swing data: {swing_data.swing_id}")
        else:
            print(f"Failed to store swing data: {swing_data.swing_id}")
        
        return success
    
    def get_swing_data(self, count: Optional[int] = None) -> List[SwingData]:
        """Get swing data for current session"""
        if not self.current_session:
            print("No active session")
            return []
        
        return self.redis_manager.get_swing_data(self.current_session, count)
    
    def log_swing_event(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> Optional[SwingEvent]:
        """Log a swing event for current session"""
        if not self.current_session:
            print("No active session")
            return None
        
        event = SwingEvent(
            session_id=self.current_session.session_id,
            event_type=event_type,
            data=data
        )
        
        if self.redis_manager.store_swing_event(event, self.current_session):
            print(f"Logged swing event: {event_type}")
            return event
        else:
            print(f"Failed to log swing event: {event_type}")
            return None
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session"""
        if not self.current_session:
            return {"error": "No active session"}
        
        # Get swing count
        swing_count = self.redis_manager.get_session_swing_count(self.current_session)
        
        return {
            "session_id": self.current_session.session_id,
            "user_id": self.current_session.user_id,
            "club_id": self.current_session.club_id,
            "session_start_time": self.current_session.session_start_time.isoformat(),
            "swing_count": swing_count,
            "club_length": self.current_session.club_length,
            "club_mass": self.current_session.club_mass,
            "impact_threshold": self.current_session.impact_threshold
        }
    
    def update_session_config(self, **kwargs) -> bool:
        """Update current session configuration"""
        if not self.current_session:
            return False
        
        # Update allowed fields
        allowed_fields = ['impact_threshold', 'face_normal_calibration']
        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(self.current_session, field, value)
        
        # Store updated config
        return self.redis_manager.store_session_config(self.current_session)
    
    def get_swing_statistics(self) -> Dict[str, Any]:
        """Get swing statistics for current session"""
        if not self.current_session:
            return {"error": "No active session"}
        
        swings = self.get_swing_data()
        if not swings:
            return {"swing_count": 0, "average_duration": 0, "average_impact_g": 0}
        
        total_duration = sum(swing.swing_duration for swing in swings)
        total_impact_g = sum(swing.impact_g_force for swing in swings)
        
        return {
            "swing_count": len(swings),
            "average_duration": total_duration / len(swings),
            "average_impact_g": total_impact_g / len(swings),
            "min_impact_g": min(swing.impact_g_force for swing in swings),
            "max_impact_g": max(swing.impact_g_force for swing in swings),
            "swing_types": list(set(swing.swing_type for swing in swings))
        }
    
    def get_imu_buffer(self, count: Optional[int] = None) -> List:
        """Get IMU buffer for current session"""
        if not self.current_session:
            return []
        
        return self.redis_manager.get_imu_buffer(self.current_session, count) 