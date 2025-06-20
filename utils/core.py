# utils/core.py

"""
core.py – Core Utility Functions

Provides high-level, application-wide utility functions, such as data caching
wrappers for Streamlit, mobile device detection logic based on browser user agents,
and a utility for loading application configuration from a JSON file.
"""

from functools import wraps
from typing import Callable, Any
import streamlit as st
import json
from pathlib import Path


def cache_data(func: Callable) -> Callable:
    """
    Decorator for caching function results using Streamlit's `st.cache_data` mechanism.

    This decorator memoizes the output of a function, improving performance by
    avoiding re-execution of expensive computations on subsequent reruns
    with the same inputs.

    Args:
        func: The function to be cached.

    Returns:
        Callable: The wrapped, cached function.
    """
    @st.cache_data(show_spinner=False) # Apply Streamlit's data caching. show_spinner=False hides default spinner.
    @wraps(func) # Preserves function metadata (e.g., name, docstring)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)
    return wrapper


def is_mobile() -> bool:
    """
    Detects if the Streamlit app is currently being viewed on a mobile device.

    This detection is based on analyzing the browser's user agent string
    stored in Streamlit's session state.

    Returns:
        bool: True if a mobile device user agent is detected, False otherwise.
    """
    # Retrieve the browser user agent string from Streamlit's session state.
    ua = st.session_state.get("_browser_user_agent", "")
    # Check for common mobile keywords (case-insensitive).
    return any(mob in ua.lower() for mob in ("iphone", "android", "mobile"))
