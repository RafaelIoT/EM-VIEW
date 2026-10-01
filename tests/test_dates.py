from datetime import date
import unittest

import pandas as pd

from utils.dates import date_bounds, filter_dates


class DateFilterTests(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame([
            {"Start Year": 2020, "Start Month": 2, "Start Day": 29, "End Year": None},
            {"Start Year": 2020, "Start Month": 2, "Start Day": None, "End Year": 2020},
            {"Start Year": 2019, "Start Month": 12, "Start Day": 31,
             "End Year": 2020, "End Month": 1, "End Day": 2},
            {"Start Year": 2021, "Start Month": None, "Start Day": None, "End Year": None},
        ])

    def test_unknown_end_does_not_exclude_start_and_boundary_is_inclusive(self):
        result = filter_dates(self.data, date(2020, 2, 29), date(2020, 2, 29))
        self.assertEqual(result.index.tolist(), [0, 1])

    def test_partial_dates_preserve_uncertainty_and_leap_year(self):
        bounds = date_bounds(self.data)
        self.assertEqual(bounds.loc[1, "latest"], pd.Timestamp("2020-02-29"))
        self.assertEqual(bounds.loc[3, "earliest"], pd.Timestamp("2021-01-01"))
        result = filter_dates(self.data, date(2020, 2, 15), date(2020, 2, 29), include_partial=False)
        self.assertEqual(result.index.tolist(), [0])

    def test_overlap_differs_from_start_and_missing_end_is_not_ongoing(self):
        result = filter_dates(self.data, date(2020, 1, 1), date(2020, 1, 2), "overlaps")
        self.assertEqual(result.index.tolist(), [2])
        self.assertTrue(filter_dates(self.data, date(2020, 1, 1), date(2020, 1, 2)).empty)
        self.assertTrue(filter_dates(self.data, date(2022, 1, 1), date(2022, 1, 2), "overlaps").empty)

    def test_reversed_period_is_empty(self):
        self.assertTrue(filter_dates(self.data, date(2021, 1, 1), date(2020, 1, 1)).empty)


if __name__ == "__main__":
    unittest.main()
