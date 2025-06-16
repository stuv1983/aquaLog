import streamlit as st
from config import VERSION, RELEASE_NOTES

def render_release_notes() -> None:
    """Render the release notes expander."""
    # MODIFICATION: Added the 'icon' parameter
    with st.sidebar.expander("📦 Release Notes", expanded=False, icon="💧"):
        st.markdown(f"**{VERSION}**")
        st.markdown(RELEASE_NOTES)