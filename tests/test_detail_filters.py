import unittest

import pandas as pd

from utils.detail_filters import filter_event_details


class DetailFilterTests(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame({"DisNo.": ["A[1]", "B", "C"], "Country": ["Japan"] * 3,
                                  "Disaster Subgroup": ["Hydrological", "Meteorological", "Hydrological"],
                                  "Disaster Subtype": ["Flood", "Storm", "Flood"],
                                  "Total Deaths": [0, None, 100], "Total Affected": [None, 0, 1000]})

    def test_reported_filter_keeps_explicit_zeros_and_requires_every_measure(self):
        result = filter_event_details(self.data, required_columns=["Total Deaths"])
        self.assertEqual(result["DisNo."].tolist(), ["A[1]", "C"])
        result = filter_event_details(self.data, required_columns=["Total Deaths", "Total Affected"])
        self.assertEqual(result["DisNo."].tolist(), ["C"])

    def test_disabled_threshold_keeps_missing_and_positive_threshold_excludes_it(self):
        self.assertEqual(len(filter_event_details(self.data)), 3)
        self.assertEqual(filter_event_details(self.data, minimum_deaths=1)["DisNo."].tolist(), ["C"])
        self.assertEqual(len(filter_event_details(self.data, minimum_affected=1001)), 0)

    def test_category_filters_and_literal_event_search(self):
        self.assertEqual(filter_event_details(self.data, subtypes=["Storm"])["DisNo."].tolist(), ["B"])
        self.assertEqual(len(filter_event_details(self.data, subgroups=["Hydrological"])), 2)
        self.assertEqual(filter_event_details(self.data, search="a[1]")["DisNo."].tolist(), ["A[1]"])


if __name__ == "__main__":
    unittest.main()
