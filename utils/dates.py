"""Inclusive date filters that preserve EM-DAT's partial-date precision."""
from datetime import date

import pandas as pd


def date_bounds(data: pd.DataFrame, prefix: str = "Start") -> pd.DataFrame:
    """Return earliest/latest possible dates without inventing missing days."""
    def part(name):
        return pd.to_numeric(
            data.get(f"{prefix} {name}", pd.Series(index=data.index, dtype=float)),
            errors="coerce",
        )

    year, month, day = part("Year"), part("Month"), part("Day")
    first_month, last_month = month.fillna(1), month.fillna(12)
    first = pd.to_datetime(
        dict(year=year, month=first_month, day=day.where(month.notna()).fillna(1)),
        errors="coerce",
    )
    last_month_start = pd.to_datetime(
        dict(year=year, month=last_month, day=1), errors="coerce"
    )
    last = pd.to_datetime(
        dict(year=year, month=last_month,
             day=day.where(month.notna()).fillna(last_month_start.dt.days_in_month)),
        errors="coerce",
    )
    return pd.DataFrame({"earliest": first, "latest": last}, index=data.index)


def filter_dates(data: pd.DataFrame, start: date, end: date,
                 match: str = "starts", include_partial: bool = True) -> pd.DataFrame:
    """Select starts in a period, or events overlapping it; boundaries inclusive.

    Partial start dates match when their possible date interval intersects the
    period. Unknown end dates fall back to the start-date interval: they are
    not assumed ongoing. A missing end month/day spans the known end year/month.
    """
    if match not in {"starts", "overlaps"}:
        raise ValueError("Date match must be starts or overlaps")
    if start > end:
        return data.iloc[:0].copy()
    bounds = date_bounds(data)
    latest = bounds["latest"]
    if match == "overlaps":
        end_bounds = date_bounds(data, "End")
        latest = end_bounds["latest"].fillna(latest)
    mask = (bounds["earliest"] <= pd.Timestamp(end)) & (latest >= pd.Timestamp(start))
    if not include_partial:
        mask &= bounds["earliest"].eq(bounds["latest"])
    return data.loc[mask].copy()
