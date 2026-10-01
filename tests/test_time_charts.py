import unittest

import pandas as pd

from utils.comparison import aggregate_impacts
from utils.time_charts import make_time_chart


class TimeChartTests(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame({"Country": ["Japan", "Japan", "Myanmar"],
                                  "Start Year": [2020, 2022, 2020], "Total Deaths": [10, None, 30]})
        self.summary = aggregate_impacts(self.data, ["Deaths"], ["Start Year", "Country"])

    def test_country_bars_are_grouped_and_missing_values_stay_missing(self):
        fig = make_time_chart(self.summary, "Deaths", "Country", "Total")
        self.assertEqual(fig.layout.barmode, "group")
        self.assertEqual([trace.name for trace in fig.data], ["Japan", "Myanmar"])
        self.assertEqual(list(fig.data[0].x), ["2020", "2021", "2022"])
        self.assertTrue(pd.isna(fig.data[0].y[1]))
        self.assertTrue(pd.isna(fig.data[0].y[2]))
        self.assertNotEqual(fig.data[0].offsetgroup, fig.data[1].offsetgroup)

    def test_lines_preserve_gaps_and_facets_have_separate_axes(self):
        fig = make_time_chart(self.summary, "Deaths", "Country", "Total", "Lines")
        self.assertFalse(fig.data[0].connectgaps)
        self.assertTrue(pd.isna(fig.data[0].y[1]))
        fig = make_time_chart(self.summary, "Deaths", "Country", "Total", "Separate panels")
        self.assertNotEqual(fig.data[0].xaxis, fig.data[1].xaxis)

    def test_all_events_and_subregion_grouping(self):
        summary = aggregate_impacts(self.data, ["Events"], ["Start Year"])
        fig = make_time_chart(summary, "Events", None, "Total")
        self.assertEqual(list(fig.data[0].y)[0], 2)
        self.assertEqual(fig.data[0].name, "All events")
        summary = self.summary.rename(columns={"Country": "Subregion"})
        fig = make_time_chart(summary, "Deaths", "Subregion", "Total")
        self.assertEqual(fig.layout.barmode, "group")


if __name__ == "__main__":
    unittest.main()
