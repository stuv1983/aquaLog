"""
email_settings.py - Email settings operations with validation
"""
import json
from typing import Dict, Optional, Any, List
from ..base import BaseRepository

class EmailSettingsRepository(BaseRepository):
    """Handles email settings operations with validation."""
    
    def get(self) -> Optional[Dict[str, Any]]:
        """Get email settings for the default user."""
        settings = self.fetch_one(
            "SELECT * FROM email_settings WHERE user_id = 1;"
        )
        
        if not settings:
            return None
            
        if settings.get("tanks"):
            try:
                settings["tanks"] = json.loads(settings["tanks"])
            except (json.JSONDecodeError, TypeError):
                settings["tanks"] = []
        
        return settings

    def save(self, **kwargs: Any) -> Dict[str, Any]:
        """Save email settings and return the saved record."""
        self._validate_settings(kwargs)
        
        if "tanks" in kwargs and isinstance(kwargs["tanks"], list):
            kwargs["tanks"] = json.dumps(kwargs["tanks"])
            
        kwargs["user_id"] = 1
        columns = ", ".join(kwargs.keys())
        placeholders = ", ".join("?" for _ in kwargs)
        values = list(kwargs.values())
        
        update_assignments = ", ".join(
            f"{key} = excluded.{key}" for key in kwargs if key != "user_id"
        )
        
        query = f"""
            INSERT INTO email_settings ({columns}) VALUES ({placeholders})
            ON CONFLICT(user_id) DO UPDATE SET {update_assignments},
                                               updated_at = datetime('now');
        """
        
        with self._connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, values)
                saved_settings = self.fetch_one(
                    "SELECT * FROM email_settings WHERE user_id = 1;"
                )
                conn.commit()
                
                if saved_settings and saved_settings.get("tanks"):
                    try:
                        saved_settings["tanks"] = json.loads(saved_settings["tanks"])
                    except (json.JSONDecodeError, TypeError):
                        saved_settings["tanks"] = []
                
                return saved_settings
            except sqlite3.IntegrityError as e:
                conn.rollback()
                if "CHECK" in str(e):
                    raise ValueError(f"Invalid settings: {str(e)}")
                raise RuntimeError(f"Database error: {str(e)}") from e
            except sqlite3.Error as e:
                conn.rollback()
                raise RuntimeError(f"Database error: {str(e)}") from e

    def _validate_settings(self, settings: Dict[str, Any]):
        """Validate email settings."""
        if "email" in settings and settings["email"] is not None:
            if not isinstance(settings["email"], str) or "@" not in settings["email"]:
                raise ValueError("Invalid email address format")
        
        if "tanks" in settings and not isinstance(settings["tanks"], list):
            raise ValueError("Tanks must be a list of tank IDs")