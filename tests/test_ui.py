"""Exercise navigation and comparison controls through Streamlit's runtime."""
from datetime import date
from pathlib import Path
import logging
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
logging.disable(logging.WARNING)


def summary_frame(at):
    return next(frame.value for frame in at.dataframe if "Coverage (%)" in frame.value.columns)


def comparison_app(source_data=None):
    data = pd.DataFrame({
        "DisNo.": ["2020-0001-JPN", "2021-0002-JPN", "2020-0003-MMR"],
        "Country": ["Japan", "Japan", "Myanmar"], "ISO": ["JPN", "JPN", "MMR"],
        "Region": ["Asia"] * 3, "Subregion": ["Eastern Asia", "Eastern Asia", "South-Eastern Asia"],
        "Classification Key": ["nat-hyd-flo-flo", "nat-met-sto-tro", "nat-hyd-flo-flo"],
        "Disaster Group": ["Natural"] * 3, "Disaster Type": ["Flood", "Storm", "Flood"],
        "Disaster Subgroup": ["Hydrological", "Meteorological", "Hydrological"],
        "Disaster Subtype": ["Riverine flood", "Tropical cyclone", "Riverine flood"],
        "Start Year": [2020, 2021, 2020], "Start Month": [2, 3, 4], "Start Day": [None, 1, 2],
        "End Year": [None, 2021, 2020], "Total Deaths": [10, None, 30],
        "Total Affected": [0, 100, None], "Total Damage ('000 US$)": [1, None, 2],
    })
    if source_data is not None:
        data = source_data
    first_year, last_year = int(data["Start Year"].min()), int(data["Start Year"].max())
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15)
    at.session_state["data"] = data
    at.session_state["metadata"] = {"Source": "Synthetic test fixture"}
    at.session_state["filename"] = "test.xlsx"
    at.session_state["info"] = "3 synthetic records"
    region = data[["Region", "Subregion", "Country"]].drop_duplicates()
    region.columns = [c.lower() for c in region]
    at.session_state["region_data"] = region
    settings = {
        "filter.disabled": False, "filter.year_min": first_year, "filter.year_max": last_year,
        "filter.start": first_year, "filter.end": last_year, "filter.classification_key": "",
        "filter.region": None, "filter.subregion": None, "filter.country": None,
        "filter.exact_dates": False, "filter.date_start": date(first_year, 1, 1),
        "filter.date_end": date(last_year, 12, 31), "filter.date_match": "starts",
        "filter.include_partial": True, "filter.groups": [], "filter.types": [],
        "region_list": [None] + sorted(region["region"].unique()),
        "subregion_list": [None] + sorted(region["subregion"].unique()),
        "country_list": [None] + sorted(region["country"].unique()),
    }
    for key, value in settings.items():
        at.session_state[key] = value
    at.run()
    at.switch_page("views/comparison.py").run()
    return at


class ComparisonUITests(unittest.TestCase):
    def test_controls_recalculate_and_empty_selection_is_supported(self):
        at = comparison_app()
        self.assertEqual(len(at.exception), 0)
        at.selectbox(key="comparison.aggregation").select("Mean per event").run()
        summary = summary_frame(at)
        japan = summary[(summary["Country"] == "Japan") & (summary["Metric"] == "Deaths")]
        self.assertEqual(japan["Value"].iloc[0], 10)
        at.selectbox(key="comparison.denominator").select("All events").run()
        summary = summary_frame(at)
        japan = summary[(summary["Country"] == "Japan") & (summary["Metric"] == "Deaths")]
        self.assertEqual(japan["Value"].iloc[0], 5)
        at.button(key="filter.countries_none").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertIn("No events match", at.info[0].value)

    def test_sidebar_disaster_and_date_filters_reach_the_view(self):
        at = comparison_app()
        at.multiselect(key="filter.types").set_value(["Storm"]).run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(summary_frame(at)["Events"].max(), 1)
        at.toggle(key="filter.exact_dates").set_value(True).run()
        at.date_input(key="filter.date_start").set_value(date(2021, 3, 2)).run()
        self.assertEqual(len(at.exception), 0)
        self.assertIn("No events match", at.info[0].value)

    def test_country_context_and_normalization_update_the_same_charts(self):
        from utils.worldbank import CONTEXT_COLUMNS
        at = comparison_app()
        context = pd.DataFrame([
            ["JPN", 2020, 100000, 1000000, 10], ["JPN", 2021, 200000, 2000000, 10],
            ["MMR", 2020, 100000, 1000000, 10],
        ], columns=CONTEXT_COLUMNS)
        at.session_state["comparison.context"] = context
        at.run()
        at.selectbox(key="comparison.normalization").select("Per 100,000 residents").run()
        self.assertEqual(len(at.exception), 0)
        frame = summary_frame(at)
        self.assertAlmostEqual(frame.query("Country == 'Myanmar' and Metric == 'Deaths'")["Value"].iloc[0], 30)
        at.multiselect(key="comparison.metrics").set_value(["Damage (current US$)"]).run()
        at.selectbox(key="comparison.normalization").select("% of event-year GDP").run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(summary_frame(at).query("Country == 'Japan'")["Value"].iloc[0], 0.1)

    def test_customization_event_search_and_downloads(self):
        at = comparison_app()
        at.selectbox(key="comparison.orientation").select("Horizontal").run()
        at.selectbox(key="comparison.order").select("Highest impact").run()
        at.checkbox(key="comparison.value_labels").set_value(True).run()
        at.text_input(key="comparison.event_search").set_value("2020-0003-MMR").run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.dataframe[-1].value), 1)
        self.assertEqual(at.dataframe[-1].value["Country"].iloc[0], "Myanmar")
        self.assertEqual(summary_frame(at)["Events"].max(), 2)  # Search is table-only.
        self.assertEqual(len(at.get("download_button")), 3)

    def test_world_bank_failure_leaves_absolute_comparison_available(self):
        import requests
        at = comparison_app()
        with patch("utils.worldbank.requests.get", side_effect=requests.ConnectionError("Test offline")):
            at.button(key="comparison.load_context").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertIn("Absolute comparisons remain available", at.warning[0].value)
        self.assertEqual(summary_frame(at)["Value"].sum(), 140)

    def test_empty_legacy_view_keeps_shared_filters_available(self):
        at = comparison_app()
        at.text_input(key="filter.classification_key").set_value("no-such-classification").run()
        at.switch_page("views/metric.py").run()
        self.assertEqual(len(at.exception), 0)
        self.assertIn("No events match", at.info[0].value)
        self.assertIn("filter.start", [widget.key for widget in at.sidebar.number_input])
        self.assertIn("filter.end", [widget.key for widget in at.sidebar.number_input])
        self.assertIn("Reset", [button.label for button in at.sidebar.button])

    def test_country_checkboxes_preserve_hidden_selections_and_reset(self):
        at = comparison_app()
        at.checkbox(key="filter.country_choice.Japan").uncheck().run()
        self.assertEqual(summary_frame(at)["Country"].unique().tolist(), ["Myanmar"])
        at.text_input(key="filter.country_search").set_value("Japan").run()
        self.assertTrue(at.session_state["filter.countries"] == ["Myanmar"])
        at.switch_page("views/table.py").run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(at.dataframe[0].value["Country"].unique().tolist(), ["Myanmar"])
        at.text_input(key="filter.country_search").set_value("").run()
        self.assertFalse(at.checkbox(key="filter.country_choice.Japan").value)
        self.assertTrue(at.checkbox(key="filter.country_choice.Myanmar").value)
        next(button for button in at.sidebar.button if button.label == "Reset").click().run()
        self.assertEqual(at.session_state["filter.countries"], ["Japan", "Myanmar"])

    def test_time_view_controls_and_country_checkboxes(self):
        at = comparison_app()
        at.switch_page("views/time.py").run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(at.selectbox(key="time.style").value, "Side-by-side bars")
        self.assertEqual(at.selectbox(key="time.dimension").value, "Country")
        at.selectbox(key="time.aggregation").select("Mean per event").run()
        at.selectbox(key="time.dimension").select("Subregion").run()
        at.checkbox(key="filter.country_choice.Japan").uncheck().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(summary_frame(at)["Subregion"].unique().tolist(), ["South-Eastern Asia"])
        at.selectbox(key="time.style").select("Separate panels").run()
        self.assertEqual(len(at.exception), 0)

    def test_detail_filters_propagate_and_reset(self):
        at = comparison_app()
        at.multiselect(key="filter.subtypes").set_value(["Riverine flood"]).run()
        self.assertEqual(summary_frame(at)["Events"].sum(), 4)  # Two measures, two events.
        at.multiselect(key="filter.reported").set_value(["Affected people"]).run()
        self.assertEqual(summary_frame(at)["Country"].unique().tolist(), ["Japan"])
        at.number_input(key="filter.minimum_deaths").set_value(11).run()
        self.assertIn("No events match", at.info[0].value)
        next(button for button in at.sidebar.button if button.label == "Reset").click().run()
        at.text_input(key="filter.event_search").set_value("2020-0003-MMR").run()
        at.switch_page("views/time.py").run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(summary_frame(at)["Country"].unique().tolist(), ["Myanmar"])

    def test_exploration_views_use_shared_filters_and_support_counts(self):
        at = comparison_app()
        at.switch_page("views/explore.py").run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.get("plotly_chart")), 2)
        at.selectbox(key="explore.display").select("Share of country total (%)").run()
        at.checkbox(key="filter.country_choice.Japan").uncheck().run()
        self.assertEqual(summary_frame(at)["Country"].unique().tolist(), ["Myanmar"])
        at.selectbox(key="explore.aggregation").select("Median per event").run()
        self.assertEqual(at.selectbox(key="explore.display").value, "Impact value")
        at.selectbox(key="explore.metric").select("Events").run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.get("plotly_chart")), 1)
        self.assertEqual(summary_frame(at)["Value"].iloc[0], 1)

    def test_country_all_buttons_ignore_search_and_geography_preserves_choices(self):
        at = comparison_app()
        at.checkbox(key="filter.country_choice.Myanmar").uncheck().run()
        at.selectbox(key="filter.subregion").select("South-Eastern Asia").run()
        self.assertIn("No events match", at.info[0].value)
        at.button(key="filter.countries_all").click().run()
        self.assertEqual(summary_frame(at)["Country"].unique().tolist(), ["Myanmar"])
        at.selectbox(key="filter.subregion").select("All").run()
        self.assertEqual(at.session_state["filter.countries"], ["Japan", "Myanmar"])
        at.text_input(key="filter.country_search").set_value("Japan").run()
        at.button(key="filter.countries_none").click().run()
        self.assertEqual(at.session_state["filter.countries"], [])
        at.button(key="filter.countries_all").click().run()
        self.assertEqual(at.session_state["filter.countries"], ["Japan", "Myanmar"])


if __name__ == "__main__":
    unittest.main()
