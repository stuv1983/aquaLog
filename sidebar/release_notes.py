# sidebar/release_notes.py

"""
release_notes.py – Release Notes Display

Renders the expandable "Release Notes" section in the sidebar. This is used to
display the application's current version number and a list of recent changes
or new features, providing users with information about updates.
"""

from __future__ import annotations # Added for type hinting consistency

import streamlit as st
from config import VERSION, RELEASE_NOTES

def render_release_notes() -> None:
    """
    Renders the collapsible "Release Notes" expander in the Streamlit sidebar.

    Displays the current application version and detailed release notes
    as configured in `config.py`.

    Returns:
        None: This function renders UI elements and does not return any value.
    """
    # Use a Streamlit expander for a collapsible section, with a relevant icon.
    with st.sidebar.expander("📦 Release Notes", expanded=False, icon="💧"):
        # Display the current version clearly.
        st.markdown(f"**{VERSION}**")
        # Display the detailed release notes.
        st.markdown(RELEASE_NOTES)