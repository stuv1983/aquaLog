from functools import wraps
from typing import Callable, Any
import streamlit as st

def cache_data(func: Callable) -> Callable:
    """
    Decorator for caching function results using Streamlit's cache mechanism.
    
    Args:
        func: The function to be cached
        
    Returns:
        Wrapped function with caching enabled
    """
    @st.cache_data(show_spinner=False)
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)
    return wrapper