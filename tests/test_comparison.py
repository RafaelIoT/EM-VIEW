import unittest

import pandas as pd

from utils.comparison import aggregate_impacts


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame({
            "Country": ["A", "A", "B", "B"],
            "Disaster Type": ["Flood", "Storm", "Flood", "Flood"],
            "Start Year": [2020, 2021, 2020, 2020],
            "Total Deaths": [10, None, 0, 30],
            "Total Affected": [0, 100, None, None],
            "Total Damage ('000 US$)": [1, None, None, 2],
        })

    def test_mean_denominators_and_reporting_coverage(self):
        reported = aggregate_impacts(self.data, ["Deaths"], aggregation="Mean per event").set_index("Country")
        all_events = aggregate_impacts(self.data, ["Deaths"], aggregation="Mean per event",
                                       denominator="All events").set_index("Country")
        self.assertEqual(reported.loc["A", "Value"], 10)
        self.assertEqual(all_events.loc["A", "Value"], 5)
        self.assertEqual(reported.loc["A", "Coverage (%)"], 50)
        self.assertEqual(reported.loc["B", "Reported"], 2)  # Explicit zero is reported.

    def test_missing_totals_stay_missing_and_currency_units_are_converted(self):
        result = aggregate_impacts(self.data, ["Affected people", "Damage (current US$)"])
        self.assertTrue(pd.isna(result.query("Country == 'B' and Metric == 'Affected people'")["Value"].iloc[0]))
        self.assertEqual(result.query("Country == 'A' and Metric == 'Damage (current US$)'")["Value"].iloc[0], 1000)

    def test_type_and_annual_groups_and_count_measure(self):
        result = aggregate_impacts(self.data, ["Deaths", "Events"], ["Country", "Disaster Type"], "Median per event")
        b = result[result["Country"] == "B"].set_index("Metric")
        self.assertEqual(b.loc["Deaths", "Value"], 15)
        self.assertEqual(b.loc["Events", "Value"], 2)
        annual = aggregate_impacts(self.data, ["Events"], ["Country", "Start Year"])
        self.assertEqual(annual["Value"].sum(), len(self.data))

    def test_empty_input_has_a_stable_schema(self):
        result = aggregate_impacts(self.data.iloc[:0], ["Deaths"])
        self.assertTrue(result.empty)
        self.assertIn("Coverage (%)", result)


if __name__ == "__main__":
    unittest.main()
