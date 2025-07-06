# tabs/inventory_tab_helpers.py

"""
inventory_tab_helpers.py – Reusable Components for Inventory Tabs

Provides generic, reusable functions for the plant and fish inventory tabs to reduce
code duplication. This includes a standardized search interface and a form for
adding new items to the master database.
"""

from __future__ import annotations
import streamlit as st
import pandas as pd
from typing import Any, Callable

from utils import show_toast

def render_inventory_search(
    item_type: str,
    repo: Any,
    owned_repo: Any,
    tank_id: int,
    display_details_fn: Callable[[pd.Series], None],
    key_prefix: str = ""
) -> None:
    """
    Renders a generic search interface for an inventory type (e.g., plants, fish).

    Args:
        item_type (str): The type of item being searched (e.g., 'plant', 'fish').
        repo (Any): The repository for the master item list.
        owned_repo (Any): The repository for the owned items.
        tank_id (int): The ID of the current tank.
        display_details_fn (Callable): A function to display the item's details.
        key_prefix (str): A prefix for Streamlit widget keys.
    """
    st.subheader(f'🔍 Search {item_type.capitalize()} Database')
    master: pd.DataFrame = repo.fetch_all()

    query = st.text_input(
        f'Search all {item_type}s to add to your inventory...',
        key=f'{key_prefix}{item_type}_search'
    ).strip().lower()

    if not query:
        return

    search_cols = [col for col in master.columns if master[col].dtype == 'object']
    if not search_cols:
        st.info(f"No searchable fields for {item_type}.")
        return

    search_series = master[search_cols].fillna('').astype(str).sum(axis=1).str.lower()
    filtered = master[search_series.str.contains(query, na=False)]

    if filtered.empty:
        st.info(f'No matching {item_type}s found in the database.')
        return

    st.write("---")
    st.write("Search Results:")
    for _, row in filtered.iterrows():
        with st.container(border=True):
            item_id = row[f'{item_type}_id']
            name = row.get(f'{item_type}_name', 'Unnamed')

            cols = st.columns([1, 4, 1])

            if 'thumbnail_url' in row and row['thumbnail_url'] and str(row['thumbnail_url']).startswith('http'):
                cols[0].image(row['thumbnail_url'], width=80)

            with cols[1]:
                display_details_fn(row)

            if cols[2].button('➕ Add to My Tank', key=f'{key_prefix}add_{item_type}_{item_id}'):
                try:
                    owned_repo.add_to_tank(item_id, tank_id, name)
                    show_toast('✅ Added', f'{name} added to your tank')
                    st.rerun()
                except Exception as e:
                    st.error(f"Couldn't add {item_type}: {e}")

def render_add_new_item_form(
    item_type: str,
    repo: Any,
    form_fields_fn: Callable[[], dict[str, Any]],
    key_prefix: str = ""
) -> None:
    """
    Renders a form to add a new item to the master database.

    Args:
        item_type (str): The type of item being added (e.g., 'plant', 'fish').
        repo (Any): The repository for the master item list.
        form_fields_fn (Callable): A function that renders the form fields and returns the data.
        key_prefix (str): A prefix for Streamlit widget keys.
    """
    with st.expander(f"➕ Add New {item_type.capitalize()} to Database"):
        with st.form(f"new_{item_type}_form", clear_on_submit=True):
            st.write(f"If a {item_type} is not in the search results, you can add it here.")
            data = form_fields_fn()
            submitted = st.form_submit_button(f"💾 Save New {item_type.capitalize()}")

            if submitted:
                if not data.get(f'{item_type}_name' if item_type == 'plant' else 'species_name'):
                    st.error(f"{item_type.capitalize()} name is required.")
                else:
                    try:
                        add_method = getattr(repo, f'add_{item_type}')
                        add_method(data)
                        show_toast("✅ Success", f"{data.get(f'{item_type}_name') or data.get('common_name')} has been added to the master database.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not save {item_type}: {e}")