import streamlit as st

st.set_page_config(layout="wide")

st.title("Streamlit Display Command Test")

# This is the exact string that causes the error in your main app.
problem_string = "A medium need in CO2 is 6-14 mg/L. A high demand in CO2 is approx. 15-25 mg/L."

st.header("1. Testing `st.caption()`")
st.write("The command below (`st.caption`) is the one likely causing the error.")
try:
    st.caption(problem_string)
    st.success("SUCCESS: `st.caption()` did NOT cause an error.")
except Exception as e:
    st.error(f"ERROR: `st.caption()` failed as expected.")
    st.exception(e)

st.divider()

st.header("2. Testing `st.text()`")
st.write("The command below (`st.text`) is the recommended fix.")
try:
    st.text(problem_string)
    st.success("SUCCESS: `st.text()` worked correctly.")
except Exception as e:
    st.error(f"ERROR: `st.text()` also failed.")
    st.exception(e)

st.divider()

st.header("3. Testing `st.warning()`")
st.write("The command below (`st.warning`) was for our diagnostic test.")
try:
    st.warning(problem_string)
    st.success("SUCCESS: `st.warning()` worked correctly.")
except Exception as e:
    st.error(f"ERROR: `st.warning()` also failed.")
    st.exception(e)
