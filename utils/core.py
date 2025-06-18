# utils/core.py

"""
core.py – Core Utility Functions

Provides high-level, application-wide utility functions, such as data caching
wrappers and mobile device detection logic based on browser user agents.
"""

from functools import wraps
from typing import Callable, Any
import streamlit as st
import json
from pathlib import Path


def cache_data(func: Callable) -> Callable:
    """
    Decorator for caching function results using Streamlit's cache mechanism.
    """
    @st.cache_data(show_spinner=False)
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)
    return wrapper


def is_mobile() -> bool:
    """
    Detect if the app is being viewed on a mobile device using Streamlit's user agent string.
    """
    ua = st.session_state.get("_browser_user_agent", "")
    return any(mob in ua.lower() for mob in ("iphone", "android", "mobile"))


def load_config(config_path: str = "config.json") -> dict:
    """
    Load configuration from a JSON file.
    """
    path = Path(config_path)
    if not path.exists():
        st.error(f"Config file not found: {config_path}")
        return {}
    with open(path, "r") as f:
        return json.load(f)
