import streamlit as st
from aqualog_db.connection import get_connection

def cycle_tab() -> None:
    st.header("🔄 Water Change & Maintenance Cycle")

    with get_connection() as conn:
        # Example: fetch last cycle dates
        cycles_df = pd.read_sql(
            "SELECT date, type, notes FROM maintenance_cycles ORDER BY datetime(date) DESC LIMIT 10",
            conn
        )

    if cycles_df.empty:
        st.info("No cycle/maintenance data available.")
        return

    # render your cycles_df as you need, e.g. a table or chart
    st.dataframe(cycles_df)
