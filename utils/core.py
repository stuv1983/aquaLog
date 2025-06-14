from functools import wraps
from typing import Callable, Any
import streamlit as st


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
