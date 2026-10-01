import unittest

import pandas as pd

from utils.comparison import aggregate_impacts
from utils.exploration import make_hazard_heatmap, rank_events


class ExplorationTests(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame({"DisNo.": ["A", "B", "C", "D"], "Country": ["Japan", "Japan", "Japan", "Myanmar"],
                                  "Disaster Type": ["Flood", "Storm", "Earthquake", "Storm"],
                                  "Total Deaths": [0, 10, 30, None], "Total Damage ('000 US$)": [1, 2, 3, None]})

    def test_heatmap_preserves_zero_missing_and_absent_pairs(self):
        summary = aggregate_impacts(self.data, ["Deaths"], ["Country", "Disaster Type"])
        fig = make_hazard_heatmap(summary)
        trace = fig.data[0]
        self.assertEqual(trace.z[0][list(trace.x).index("Flood")], 0)
        self.assertTrue(pd.isna(trace.z[1][list(trace.x).index("Storm")]))
        self.assertTrue(pd.isna(trace.z[1][list(trace.x).index("Flood")]))
        shares = make_hazard_heatmap(summary, display="Share of country total (%)")
        self.assertEqual(shares.data[0].z[0][list(trace.x).index("Storm")], 25)
        coverage = make_hazard_heatmap(summary, display="Reporting coverage (%)")
        self.assertEqual(coverage.data[0].z[1][list(trace.x).index("Storm")], 0)

    def test_zero_country_total_has_no_imputed_shares(self):
        summary = aggregate_impacts(self.data.iloc[[0]], ["Deaths"], ["Country", "Disaster Type"])
        fig = make_hazard_heatmap(summary, display="Share of country total (%)")
        self.assertTrue(pd.isna(fig.data[0].z[0][0]))

    def test_rankings_exclude_missing_keep_zero_and_convert_damage(self):
        ranked = rank_events(self.data, "Deaths")
        self.assertEqual(ranked["DisNo."].tolist(), ["C", "B", "A"])
        self.assertEqual(ranked["Deaths (people)"].tolist(), [30, 10, 0])
        ranked = rank_events(self.data, "Damage (current US$)", 2)
        self.assertEqual(ranked["Damage (current US$) (US$)"].tolist(), [3000, 2000])


if __name__ == "__main__":
    unittest.main()
