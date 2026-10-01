import io
import json
import unittest
import zipfile

import pandas as pd

from utils.comparison import aggregate_impacts
from utils.comparison_charts import country_colors, make_comparison_chart
from utils.comparison_exports import analysis_bundle, summary_for_export


class ChartAndExportTests(unittest.TestCase):
    def test_annual_chart_preserves_missing_years(self):
        data = pd.DataFrame({"Country": ["Japan", "Japan"], "Start Year": [2020, 2022], "Total Deaths": [10, 20]})
        frame = aggregate_impacts(data, ["Deaths"], ["Country", "Start Year"])
        fig = make_comparison_chart(frame, "Deaths", "Start Year", ["Japan"], {"Japan": "#123456"}, "Total")
        self.assertEqual(list(fig.data[0].x), [2020, 2021, 2022])
        self.assertTrue(pd.isna(fig.data[0].y[1]))
        self.assertFalse(fig.data[0].connectgaps)

    def test_horizontal_log_chart_and_stable_colors(self):
        data = pd.DataFrame({"Country": ["Japan", "Myanmar"], "Total Deaths": [10, 20]})
        frame = aggregate_impacts(data, ["Deaths"])
        colors = country_colors(["Myanmar", "Japan"], "Accessible")
        self.assertEqual(colors, country_colors(["Japan", "Myanmar"], "Accessible"))
        fig = make_comparison_chart(frame, "Deaths", "Country", ["Japan", "Myanmar"], colors,
                                     "Total", orientation="Horizontal", log_scale=True, order="Highest impact")
        self.assertEqual(fig.layout.xaxis.type, "log")
        self.assertEqual(fig.data[0].orientation, "h")
        self.assertEqual(fig.layout.yaxis.categoryarray[0], "Myanmar")

    def test_export_preserves_missing_values_units_settings_and_all_source_columns(self):
        summary = pd.DataFrame({"Country": ["Japan", "Myanmar"], "Value": [0, None]})
        events = pd.DataFrame({"DisNo.": ["2020-0001-JPN"], "Location": ["Tokyo"],
                               "Total Damage ('000 US$)": [1]})
        settings = {"aggregation": "Mean per event", "units": {"Damage": "US$"}, "start_date": "2020-01-01"}
        bundle = analysis_bundle({"country_summary": summary, "filtered_events": events}, settings)
        with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
            restored = pd.read_csv(archive.open("country_summary.csv"))
            self.assertEqual(restored["Value"].iloc[0], 0)
            self.assertTrue(pd.isna(restored["Value"].iloc[1]))
            self.assertEqual(json.loads(archive.read("analysis.json")), settings)
            source = pd.read_csv(archive.open("filtered_events.csv"))
            self.assertEqual(source["Location"].iloc[0], "Tokyo")
            self.assertEqual(source["Total Damage ('000 US$)"].iloc[0], 1)

    def test_standalone_summary_includes_rate_units_and_period(self):
        result = summary_for_export(pd.DataFrame({"Metric": ["Deaths"], "Value": [2.5]}), {
            "units": {"Deaths": "people per 100,000 residents"}, "start_date": "2020-01-01",
            "end_date": "2021-12-31", "aggregation": "Mean per event",
            "normalization": "Per 100,000 residents", "average_denominator": "Reported events",
        })
        self.assertEqual(result["Unit"].iloc[0], "people per 100,000 residents")
        self.assertEqual(result["Start date"].iloc[0], "2020-01-01")
        self.assertEqual(result["Aggregation"].iloc[0], "Mean per event")


if __name__ == "__main__":
    unittest.main()
