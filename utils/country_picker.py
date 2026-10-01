"""Searchable country checkboxes with selection preserved across reruns."""
import streamlit as st


def _change_country(country, widget_key):
    selected = set(st.session_state["filter.countries"])
    if st.session_state[widget_key]:
        selected.add(country)
    else:
        selected.discard(country)
    st.session_state["filter.countries"] = sorted(selected)


def _select_scope(options, select):
    selected = set(st.session_state["filter.countries"])
    selected = selected.union(options) if select else selected.difference(options)
    st.session_state["filter.countries"] = sorted(selected)


def country_checkboxes(options):
    """All/none applies to the geographic scope, independent of search text.

    Persist the selection separately from widget state: Streamlit removes
    checkbox state when search or geography hides its widget.
    """
    options = sorted(options)
    st.sidebar.markdown("**Countries**")
    search = st.sidebar.text_input("Find a country", key="filter.country_search")
    all_button, none_button = st.sidebar.columns(2)
    all_button.button("Select all", key="filter.countries_all", width="stretch",
                      help="Select every country in the current region/subregion, including countries hidden by search.",
                      on_click=_select_scope, args=(options, True))
    none_button.button("Clear all", key="filter.countries_none", width="stretch",
                       help="Clear every country in the current region/subregion, including countries hidden by search.",
                       on_click=_select_scope, args=(options, False))
    selected = set(st.session_state["filter.countries"])
    st.sidebar.caption(f"{len(selected.intersection(options))} of {len(options)} countries selected")
    visible = [name for name in options if search.casefold() in name.casefold()]
    with st.sidebar.container(height=min(240, max(75, 38 * len(visible) + 10)), border=False):
        for country in visible:
            key = f"filter.country_choice.{country}"
            st.session_state[key] = country in selected
            st.checkbox(country, key=key, on_change=_change_country, args=(country, key))
        if not visible:
            st.caption("No countries match this search.")
