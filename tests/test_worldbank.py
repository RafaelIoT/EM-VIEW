import unittest
from unittest.mock import Mock, patch

import pandas as pd

from utils.comparison import aggregate_impacts
from utils.worldbank import CONTEXT_COLUMNS, country_snapshot, fetch_country_indicators


class WorldBankTests(unittest.TestCase):
    def setUp(self):
        self.context = pd.DataFrame([
            ["JPN", 2020, 100000, 1000000, 10],
            ["JPN", 2021, 200000, None, None],
            ["JPN", 2022, 300000, 5000000, 16],
        ], columns=CONTEXT_COLUMNS)
        self.events = pd.DataFrame({
            "Country": ["Japan"] * 3, "ISO": ["JPN"] * 3,
            "Start Year": [2020, 2021, 2023], "Total Deaths": [10, 10, 100],
            "Total Damage ('000 US$)": [100, 100, None],
        })

    def test_exact_event_year_population_and_missing_denominators(self):
        row = aggregate_impacts(self.events, ["Deaths"], normalization="Per 100,000 residents",
                                 context=self.context).iloc[0]
        self.assertEqual(row["Value"], 15)  # 10 + 5; no 2023 fallback.
        self.assertEqual(row["Reported"], 3)
        self.assertEqual(row["Eligible"], 2)
        self.assertEqual(row["Missing context"], 1)
        mean = aggregate_impacts(self.events, ["Deaths"], aggregation="Mean per event",
                                  normalization="Per 100,000 residents", context=self.context).iloc[0]
        self.assertEqual(mean["Value"], 7.5)

    def test_gdp_share_matches_currency_units_and_rejects_adjusted_damage(self):
        row = aggregate_impacts(self.events, ["Damage (current US$)"],
                                 normalization="% of event-year GDP", context=self.context).iloc[0]
        self.assertEqual(row["Value"], 10)
        self.assertEqual(row["Missing context"], 1)
        with self.assertRaises(ValueError):
            aggregate_impacts(self.events, ["Damage (adjusted US$)"],
                              normalization="% of event-year GDP", context=self.context)

    def test_context_snapshot_never_uses_future_values_and_exposes_fallback_year(self):
        snapshot = country_snapshot(self.context, 2021).iloc[0]
        self.assertEqual(snapshot["Population"], 200000)
        self.assertEqual(snapshot["GDP (current US$)"], 1000000)
        self.assertEqual(snapshot["GDP (current US$) year"], 2020)

    @patch("utils.worldbank.requests.get")
    def test_pagination_and_api_missing_values(self, get):
        responses = []
        for indicator, value in [("SP.POP.TOTL", 100000), ("NY.GDP.MKTP.CD", None)]:
            response = Mock()
            response.json.return_value = [{"pages": 2, "lastupdated": "2026-09-01"}, [{
                "countryiso3code": "JPN", "date": "2020", "indicator": {"id": indicator}, "value": value,
            }]]
            responses.append(response)
        get.side_effect = responses
        result = fetch_country_indicators(("JPN",), 2020, 2021)
        self.assertEqual(get.call_count, 2)
        self.assertIn("&page=2", get.call_args.args[0])
        self.assertIn("date=2020:2021", get.call_args.args[0])
        self.assertTrue(pd.isna(result["GDP (current US$)"].iloc[0]))
        self.assertEqual(result.attrs["last_updated"], "2026-09-01")

    @patch("utils.worldbank.requests.get")
    def test_api_error_is_not_misrepresented_as_an_empty_success(self, get):
        get.return_value.json.return_value = [{"message": [{"value": "Invalid value"}]}]
        with self.assertRaises(ValueError):
            fetch_country_indicators(("JPN",), 2020, 2021)


if __name__ == "__main__":
    unittest.main()
