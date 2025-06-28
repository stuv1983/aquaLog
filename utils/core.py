# utils/core.py

"""
core.py – Core Utility Functions

Provides high-level, application-wide utility functions, such as data caching
wrappers for Streamlit, mobile device detection logic based on browser user agents,
and a utility for loading application configuration from a JSON file.
"""

from __future__ import annotations # Added for type hinting consistency

from functools import wraps
from typing import Callable, Any
import streamlit as st
import json
from pathlib import Path


def cache_data(func: Callable) -> Callable:
    """
    Decorator for caching function results using Streamlit's `st.cache_data` mechanism.

    This decorator memoizes (stores the results of expensive function calls
    and returns the cached result when the same inputs occur again) the output
    of a function. This significantly improves performance by avoiding re-execution
    of costly computations on subsequent Streamlit reruns when the inputs remain identical.

    Args:
        func (Callable): The function to be cached.

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

    This detection is based on analyzing the browser's user agent string, which is
    automatically stored by Streamlit in its `st.session_state` (under `_browser_user_agent`).

    Returns:
        bool: True if a mobile device user agent (containing keywords like
              "iphone", "android", "mobile") is detected, False otherwise.
    """
    # Retrieve the browser user agent string from Streamlit's session state.
    ua = st.session_state.get("_browser_user_agent", "")
    # Check for common mobile keywords (case-insensitive).
    return any(mob in ua.lower() for mob in ("iphone", "android", "mobile"))