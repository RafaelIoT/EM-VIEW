"""Country-level impact comparisons with explicit reporting denominators."""
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ImpactMetric:
    column: str | None
    unit: str
    factor: float = 1


METRICS = {
    "Events": ImpactMetric(None, "country disaster records"),
    "Deaths": ImpactMetric("Total Deaths", "people"),
    "Affected people": ImpactMetric("Total Affected", "people"),
    "Injured people": ImpactMetric("No. Injured", "people"),
    "Homeless people": ImpactMetric("No. Homeless", "people"),
    "Damage (current US$)": ImpactMetric("Total Damage ('000 US$)", "US$", 1000),
    "Damage (adjusted US$)": ImpactMetric("Total Damage, Adjusted ('000 US$)", "US$", 1000),
}
AGGREGATIONS = ["Total", "Mean per event", "Median per event"]
DENOMINATORS = ["Reported events", "All events"]


def aggregate_impacts(data: pd.DataFrame, metrics: list[str],
                      dimensions: list[str] | None = None,
                      aggregation: str = "Total",
                      denominator: str = "Reported events") -> pd.DataFrame:
    """Produce tidy values and reporting coverage for each country/group.

    A blank impact remains unavailable, including groups with no reported
    values. Mean uses reported events by default. All-events mean divides the
    observed sum by all records, and is explicitly an observed-impact average.
    Medians always use reported values; missing impacts are never imputed.
    Damage values are converted from thousands of US$ to US$.
    """
    dimensions = dimensions or ["Country"]
    if aggregation not in AGGREGATIONS or denominator not in DENOMINATORS:
        raise ValueError("Unsupported aggregation or denominator")
    if any(metric not in METRICS for metric in metrics):
        raise ValueError("Unsupported impact metric")
    columns = dimensions + ["Metric", "Value", "Events", "Reported", "Missing",
                            "Coverage (%)", "Denominator"]
    rows = []
    for keys, group in data.groupby(dimensions, dropna=False, observed=True, sort=True):
        keys = keys if isinstance(keys, tuple) else (keys,)
        events = len(group)
        for name in metrics:
            metric = METRICS[name]
            values = (pd.to_numeric(group[metric.column], errors="coerce") * metric.factor
                      if metric.column else pd.Series(1.0, index=group.index))
            reported = int(values.count())
            total = values.sum(min_count=1)
            divisor = reported
            if name == "Events":
                value, divisor = events, events
            elif aggregation == "Total":
                value = total
            elif aggregation == "Median per event":
                value = values.median() if reported else float("nan")
            else:
                divisor = events if denominator == "All events" else reported
                value = total / divisor if divisor else float("nan")
            rows.append(dict(zip(dimensions, keys)) | {
                "Metric": name, "Value": value, "Events": events, "Reported": reported,
                "Missing": events - reported, "Coverage (%)": reported / events * 100,
                "Denominator": divisor,
            })
    return pd.DataFrame(rows, columns=columns)
