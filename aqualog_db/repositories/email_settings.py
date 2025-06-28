# aqualog_db/repositories/email_settings.py

"""
email_settings.py – Email Settings Repository

Manages user settings for email notifications. Handles saving and retrieving
preferences for the weekly summary email, such as which tanks and data fields
to include in the report. This ensures that email preferences are persisted
and accessible across application sessions.
"""

from __future__ import annotations # Added for type hinting consistency

import json
from typing import Dict, Optional, Any, List, TypedDict # Added TypedDict for more specific type hints
from ..base import BaseRepository
import sqlite3 # Imported for type hinting sqlite3.Error and IntegrityError

# Define a TypedDict for the structure of an email settings record.
class EmailSettingsRecord(TypedDict, total=False):
    """Represents a single row/record from the `email_settings` table."""
    user_id: int
    email: Optional[str]
    tanks: List[int] # Stored as JSON string in DB, but handled as List[int] in app
    include_type: bool
    include_date: bool
    include_notes: bool
    include_cost: bool
    include_stats: bool
    include_cycle: bool
    created_at: str
    updated_at: str

class EmailSettingsRepository(BaseRepository):
    """
    Handles database operations for storing and retrieving user email settings.

    This repository manages preferences for automated weekly summary emails,
    including the recipient email address, selected tanks, and included data fields.
    It currently assumes a single user (user_id = 1) for simplicity.
    """
    
    def get(self) -> Optional[EmailSettingsRecord]: # Updated return type
        """
        Retrieves the email settings for the default user (user_id = 1) from the database.

        The 'tanks' field, if present and not None, is deserialized from a JSON string
        back into a Python list for easier use in the application.

        Returns:
            Optional[EmailSettingsRecord]: A dictionary representing the email settings,
                                      or `None` if no settings are found for user_id 1.

        Raises:
            RuntimeError: If a database error occurs during the fetch operation.
        """
        settings_dict = self.fetch_one(
            "SELECT * FROM email_settings WHERE user_id = 1;"
        )
        
        if not settings_dict:
            return None
        
        # Cast to EmailSettingsRecord here for type checkers
        settings: EmailSettingsRecord = settings_dict
            
        # Attempt to deserialize the 'tanks' field from JSON string to a list
        if settings.get("tanks"):
            try:
                settings["tanks"] = json.loads(str(settings["tanks"])) # Ensure it's treated as string for json.loads
            except (json.JSONDecodeError, TypeError):
                # If deserialization fails (e.g., malformed JSON), default to an empty list
                settings["tanks"] = []
        
        return settings

    def save(self, **kwargs: Any) -> EmailSettingsRecord: # Updated return type
        """
        Saves or updates email settings for the default user (user_id = 1).

        This method handles serialization of the 'tanks' list to a JSON string
        before saving to the database. It uses an UPSERT (INSERT OR REPLACE/UPDATE)
        mechanism based on the `user_id` primary key to either insert new settings
        or update existing ones.

        Args:
            **kwargs (Any): Keyword arguments representing the email settings to save.
                            Expected keys and their types are:
                            - `email` (str, optional): The recipient's email address.
                            - `tanks` (List[int], optional): A list of tank IDs to include in the summary.
                            - `include_type` (bool, optional): Whether to include maintenance type.
                            - `include_date` (bool, optional): Whether to include maintenance date.
                            - `include_notes` (bool, optional): Whether to include maintenance notes.
                            - `include_cost` (bool, optional): Whether to include maintenance cost.
                            - `include_stats` (bool, optional): Whether to include water test statistics.
                            - `include_cycle` (bool, optional): Whether to include nitrogen cycle status.

        Returns:
            EmailSettingsRecord: A dictionary representing the saved email settings,
                                 with the 'tanks' field deserialized back to a Python list.

        Raises:
            ValueError: If input validation fails (e.g., invalid email format,
                        'tanks' is not a list, or other check constraints are violated).
            RuntimeError: If a database error occurs during the save operation.
        """
        self._validate_settings(kwargs)
        
        # Serialize the 'tanks' list to a JSON string for storage in DB
        if "tanks" in kwargs and isinstance(kwargs["tanks"], list):
            kwargs["tanks"] = json.dumps(kwargs["tanks"])
            
        kwargs["user_id"] = 1 # Hardcode user_id for the single-user setup
        
        # Prepare columns and placeholders for the INSERT part of the UPSERT
        columns = ", ".join(kwargs.keys())
        placeholders = ", ".join("?" for _ in kwargs)
        values = list(kwargs.values())
        
        # Prepare assignments for the UPDATE part of the UPSERT (ON CONFLICT)
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
                # Fetch the saved settings to confirm and return the current state
                saved_settings_dict = self.fetch_one(
                    "SELECT * FROM email_settings WHERE user_id = 1;"
                )
                conn.commit()
                
                # Cast to EmailSettingsRecord here
                saved_settings: EmailSettingsRecord = saved_settings_dict
                
                # After successful save, deserialize 'tanks' back to a list for the return value
                if saved_settings and saved_settings.get("tanks"):
                    try:
                        saved_settings["tanks"] = json.loads(str(saved_settings["tanks"]))
                    except (json.JSONDecodeError, TypeError):
                        saved_settings["tanks"] = []
                
                return saved_settings
            except sqlite3.IntegrityError as e:
                conn.rollback()
                if "CHECK" in str(e):
                    # Catch specific SQLite CHECK constraint violations (e.g., malformed email regex)
                    raise ValueError(f"Invalid settings: {str(e)}")
                raise RuntimeError(f"Database error: {str(e)}") from e
            except sqlite3.Error as e:
                conn.rollback()
                raise RuntimeError(f"Database error: {str(e)}") from e

    def _validate_settings(self, settings: Dict[str, Any]) -> None: # Using Dict[str, Any] as kwargs is flexible
        """
        Performs validation on the provided email settings dictionary.

        Args:
            settings (Dict[str, Any]): A dictionary containing the settings to validate.

        Raises:
            ValueError: If the 'email' address format is invalid (missing '@' or domain part),
                        or if 'tanks' is provided but is not a list.
        """
        if "email" in settings and settings["email"] is not None:
            # Basic email format validation (presence of '@' and a domain part)
            if not isinstance(settings["email"], str) or "@" not in settings["email"]:
                raise ValueError("Invalid email address format")
        
        if "tanks" in settings and not isinstance(settings["tanks"], list):
            # Ensure 'tanks' is always a list of tank IDs
            raise ValueError("Tanks must be a list of tank IDs")
        
        # Additional validation for boolean flags could be added here if necessary
        # e.g., for 'include_type', 'include_date', etc.