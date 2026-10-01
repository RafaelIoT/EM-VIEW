"""Exercise navigation and comparison controls through Streamlit's runtime."""
from datetime import date
from pathlib import Path
import logging
import unittest

import pandas as pd
from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
logging.getLogger("streamlit.runtime.scriptrunner_utils.script_run_context").setLevel(logging.ERROR)


def summary_frame(at):
    return next(frame.value for frame in at.dataframe if "Coverage (%)" in frame.value.columns)


def comparison_app():
    data = pd.DataFrame({
        "DisNo.": ["2020-0001-JPN", "2021-0002-JPN", "2020-0003-MMR"],
        "Country": ["Japan", "Japan", "Myanmar"], "ISO": ["JPN", "JPN", "MMR"],
        "Region": ["Asia"] * 3, "Subregion": ["Eastern Asia", "Eastern Asia", "South-Eastern Asia"],
        "Classification Key": ["nat-hyd-flo-flo", "nat-met-sto-tro", "nat-hyd-flo-flo"],
        "Disaster Group": ["Natural"] * 3, "Disaster Type": ["Flood", "Storm", "Flood"],
        "Start Year": [2020, 2021, 2020], "Start Month": [2, 3, 4], "Start Day": [None, 1, 2],
        "End Year": [None, 2021, 2020], "Total Deaths": [10, None, 30],
        "Total Affected": [0, 100, None], "Total Damage ('000 US$)": [1, None, 2],
    })
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15)
    at.session_state["data"] = data
    at.session_state["metadata"] = {"Source": "Synthetic test fixture"}
    at.session_state["filename"] = "test.xlsx"
    at.session_state["info"] = "3 synthetic records"
    region = data[["Region", "Subregion", "Country"]].drop_duplicates()
    region.columns = [c.lower() for c in region]
    at.session_state["region_data"] = region
    settings = {
        "filter.disabled": False, "filter.year_min": 2020, "filter.year_max": 2021,
        "filter.start": 2020, "filter.end": 2021, "filter.classification_key": "",
        "filter.region": None, "filter.subregion": None, "filter.country": None,
        "filter.exact_dates": False, "filter.date_start": date(2020, 1, 1),
        "filter.date_end": date(2021, 12, 31), "filter.date_match": "starts",
        "filter.include_partial": True, "filter.groups": [], "filter.types": [],
        "region_list": [None, "Asia"],
        "subregion_list": [None, "Eastern Asia", "South-Eastern Asia"],
        "country_list": [None, "Japan", "Myanmar"],
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
        at.multiselect(key="comparison.countries").set_value([]).run()
        self.assertEqual(len(at.exception), 0)
        self.assertIn("Select at least one country", at.info[0].value)

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


if __name__ == "__main__":
    unittest.main()
