from datetime import date
from fnmatch import translate

import pandas as pd
import streamlit as st

from utils.dates import filter_dates
from utils.country_picker import country_checkboxes
from utils.comparison import METRICS
from utils.detail_filters import filter_event_details

DOC_URI = "https://doc.emdat.be/docs"
CLASSIF_KEY_DOC_URI = (
    f"{DOC_URI}/data-structure-and-content/disaster-classification-system/"
    f"#main-classification-tree"
)


def init_sidebar_filters() -> None:
    """Initialize sidebar filters."""
    ss = st.session_state
    if ss.pop("filter.reset_pending", False):
        set_filters_to_default()

    # Not having session states mean that data has not been uploaded and that
    # filters should be disabled.
    filters_disabled = "data" not in ss

    # Set default if data
    if not filters_disabled:

        # Initialize filters once enabled
        if "filter.disabled" not in st.session_state:
            set_filters_to_default()
        if "filter.countries" not in ss:
            country = ss.get("filter.country")
            ss["filter.countries"] = [country] if country else sorted(ss["data"]["Country"].dropna().unique())
        # Retained for older sessions and the legacy map view.
        ss["filter.country"] = None

        col1, col2 = st.sidebar.columns(2)

        col1.number_input(
            label='**Start year**',
            min_value=ss["filter.year_min"],
            max_value=ss["filter.year_max"],
            key='filter.start'
        )

        col2.number_input(
            label='**End year**',
            min_value=ss["filter.year_min"],
            max_value=ss["filter.year_max"],
            key='filter.end'
        )

        country_checkboxes([country for country in ss['country_list'] if country is not None])

        st.sidebar.toggle("Use exact dates", key="filter.exact_dates")
        if ss["filter.exact_dates"]:
            ss.setdefault("filter.date_start", date(ss["filter.start"], 1, 1))
            ss.setdefault("filter.date_end", date(ss["filter.end"], 12, 31))
            st.sidebar.date_input(
                "Start date", key="filter.date_start",
                min_value=date(ss["filter.year_min"], 1, 1),
                max_value=date(ss["filter.year_max"], 12, 31),
            )
            st.sidebar.date_input(
                "End date", key="filter.date_end",
                min_value=date(ss["filter.year_min"], 1, 1),
                max_value=date(ss["filter.year_max"], 12, 31),
            )
        st.sidebar.selectbox(
            "Date match", ["starts", "overlaps"], key="filter.date_match",
            format_func=lambda x: "Starts in period" if x == "starts" else "Overlaps period",
            help="Unknown end dates use the start date; they are not assumed ongoing.",
        )
        st.sidebar.checkbox(
            "Include partial start dates", key="filter.include_partial",
            help="Include events when their known year/month could fall in the selected period.",
        )
        start_date, end_date = get_filter_period()
        if start_date > end_date:
            st.sidebar.warning("Start must be on or before end.")

        st.sidebar.multiselect(
            "Disaster groups", sorted(ss["data"]["Disaster Group"].dropna().unique()),
            key="filter.groups", help="Leave empty to include all groups.",
        )
        st.sidebar.multiselect(
            "Disaster types", sorted(ss["data"]["Disaster Type"].dropna().unique()),
            key="filter.types", help="Leave empty to include all types.",
        )

        with st.sidebar.expander("More event filters"):
            for column, key in [("Disaster Subgroup", "filter.subgroups"), ("Disaster Subtype", "filter.subtypes")]:
                if column in ss["data"]:
                    st.multiselect(column + "s", sorted(ss["data"][column].dropna().unique()),
                                   key=key, help="Leave empty to include all categories.")
            available = [name for name, spec in METRICS.items() if spec.column and spec.column in ss["data"]]
            st.multiselect("Require reported values", available, key="filter.reported",
                           help="Require a reported value for every selected measure. Explicit zeros count as reported.")
            for column, label, key in [("Total Deaths", "Minimum deaths per event", "filter.minimum_deaths"),
                                        ("Total Affected", "Minimum affected per event", "filter.minimum_affected")]:
                if column in ss["data"]:
                    st.number_input(label, min_value=0, step=1, key=key,
                                    help="0 disables the threshold. A positive threshold excludes missing impacts.")
            st.text_input("Search events in all views", key="filter.event_search",
                           help="Search ID, name, location, country or disaster type/subtype.")

        st.sidebar.text_input(
            label="**Classification Key**",
            key="filter.classification_key",
            help="Enter the key or its initial part to filter"
        )
        st.sidebar.caption(
            f"_Check classification keys [here]({CLASSIF_KEY_DOC_URI})._"
        )

        st.sidebar.selectbox(
            label="**Region**",
            options=ss['region_list'],
            key="filter.region",
            format_func=lambda x: 'All' if x is None else x,
            on_change=process_region
        )

        st.sidebar.selectbox(
            label="**Subregion**",
            options=ss['subregion_list'],
            key="filter.subregion",
            format_func=lambda x: 'All' if x is None else x,
            on_change=process_subregion
        )

        st.sidebar.button(
            "Reset",
            type="primary",
            on_click=set_filters_to_default
        )

        st.sidebar.divider()


def process_region() -> None:
    """Process region and update other levels accordingly."""
    ss = st.session_state
    rd = ss['region_data']
    region = ss['filter.region']
    subregion = ss['filter.subregion']
    country = ss['filter.country']
    if region:
        valid_data = rd[rd['region'] == region]
        if subregion not in valid_data['subregion'].values:
            ss['filter.subregion'] = None
        if country not in valid_data['country'].values:
            ss['filter.country'] = None
        ss['subregion_list'] = [None] + sorted(valid_data['subregion'].unique())
        ss['country_list'] = [None] + sorted(valid_data['country'].unique())
    else:
        ss['filter.subregion'] = None
        ss['filter.country'] = None
        ss['subregion_list'] = [None] + sorted(rd['subregion'].unique())
        ss['country_list'] = [None] + sorted(rd['country'].unique())

def process_subregion() -> None:
    """Process subregion and update other levels accordingly."""
    ss = st.session_state
    rd = ss['region_data']
    region = ss['filter.region']
    subregion = ss['filter.subregion']
    country = ss['filter.country']
    if subregion:
        valid_data = rd[rd['subregion'] == subregion]
        if region not in valid_data['region'].values:
            ss['filter.region'] = valid_data.iloc[0]['region']
        if country not in valid_data['country'].values:
            ss['filter.country'] = None
        ss['country_list'] = [None] + sorted(valid_data['country'].unique())
    else:
        ss['filter.country'] = None
        if region:
            valid_data = rd[rd['region'] == region]
            ss['country_list'] = [None] + sorted(valid_data['country'].unique())
        else:
            ss['country_list'] = [None] + sorted(rd['country'].unique())


def get_filter_period() -> tuple[date, date]:
    """Return the active inclusive period for views and exports."""
    ss = st.session_state
    if ss.get("filter.exact_dates", False):
        return (ss.get("filter.date_start", date(ss["filter.start"], 1, 1)),
                ss.get("filter.date_end", date(ss["filter.end"], 12, 31)))
    return date(ss["filter.start"], 1, 1), date(ss["filter.end"], 12, 31)


def get_filtered_data() -> pd.DataFrame:
    """Get filtered data based on filters session states"""
    ss = st.session_state

    # Get filters states
    start, end = get_filter_period()
    classification_key = ss["filter.classification_key"].strip()
    region = ss["filter.region"]
    subregion = ss["filter.subregion"]

    # Initiate filtering
    data_filtered = filter_dates(
        ss['data'], start, end, ss.get("filter.date_match", "starts"),
        ss.get("filter.include_partial", True),
    )

    # Filter by classification key
    data_filtered = data_filtered[
        data_filtered['Classification Key'].str.match(
            translate(classification_key + '*'), na=False
        )
    ]

    if ss.get("filter.groups"):
        data_filtered = data_filtered[data_filtered['Disaster Group'].isin(ss['filter.groups'])]
    if ss.get("filter.types"):
        data_filtered = data_filtered[data_filtered['Disaster Type'].isin(ss['filter.types'])]

    # Filter by region, subregion, country
    if region:
        data_filtered = data_filtered[data_filtered['Region'] == region]
    if subregion:
        data_filtered = data_filtered[data_filtered['Subregion'] == subregion]
    data_filtered = data_filtered[data_filtered['Country'].isin(ss["filter.countries"])]
    return filter_event_details(
        data_filtered, ss.get("filter.subgroups", []), ss.get("filter.subtypes", []),
        [METRICS[name].column for name in ss.get("filter.reported", [])],
        ss.get("filter.minimum_deaths", 0), ss.get("filter.minimum_affected", 0),
        ss.get("filter.event_search", ""),
    )


def set_filters_to_default() -> None:
    """Set or reset filters to default values"""
    ss = st.session_state
    if "data" not in ss:
        return
    data = ss["data"]
    rd = ss['region_data']
    ss['filter.disabled'] = False
    year_min = int(data['Start Year'].min())
    year_max = int(data['Start Year'].max())
    ss['filter.year_min'] = year_min
    ss['filter.year_max'] = year_max
    ss['filter.start'] = year_min
    ss['filter.end'] = year_max
    ss['filter.exact_dates'] = False
    ss['filter.date_start'] = date(year_min, 1, 1)
    ss['filter.date_end'] = date(year_max, 12, 31)
    ss['filter.date_match'] = "starts"
    ss['filter.include_partial'] = True
    ss['filter.groups'] = []
    ss['filter.types'] = []
    ss['filter.subgroups'] = []
    ss['filter.subtypes'] = []
    ss['filter.reported'] = []
    ss['filter.minimum_deaths'] = 0
    ss['filter.minimum_affected'] = 0
    ss['filter.event_search'] = ""
    ss['filter.classification_key'] = ""
    ss['filter.region'] = None
    ss['filter.subregion'] = None
    ss['filter.country'] = None
    ss['filter.countries'] = sorted(data['Country'].dropna().unique())
    ss['filter.country_search'] = ""
    ss['region_list'] = [None] + sorted(rd['region'].unique())
    ss['subregion_list'] = [None] + sorted(rd['subregion'].unique())
    ss['country_list'] = [None] + sorted(rd['country'].unique())
