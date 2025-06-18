# sidebar/release_notes.py

"""
release_notes.py – Release Notes Display

Renders the expandable "Release Notes" section in the sidebar. This is used to
display the application's current version number and a list of recent changes
or new features.
"""

import streamlit as st
from config import VERSION, RELEASE_NOTES

def render_release_notes() -> None:
    """Render the release notes expander."""
    # MODIFICATION: Added the 'icon' parameter
    with st.sidebar.expander("📦 Release Notes", expanded=False, icon="💧"):
        st.markdown(f"**{VERSION}**")
        st.markdown(RELEASE_NOTES)