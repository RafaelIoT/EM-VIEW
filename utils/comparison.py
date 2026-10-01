"""Country-level impact comparisons with explicit reporting denominators."""
from dataclasses import dataclass

import pandas as pd

from utils.worldbank import attach_event_context


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
NORMALIZATIONS = ["Absolute", "Per 100,000 residents", "% of event-year GDP"]


def aggregate_impacts(data: pd.DataFrame, metrics: list[str],
                      dimensions: list[str] | None = None,
                      aggregation: str = "Total",
                      denominator: str = "Reported events",
                      normalization: str = "Absolute",
                      context: pd.DataFrame | None = None) -> pd.DataFrame:
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
    if normalization not in NORMALIZATIONS:
        raise ValueError("Unsupported normalization")
    if normalization == "% of event-year GDP" and any(name != "Damage (current US$)" for name in metrics):
        raise ValueError("GDP normalization requires damage in current US dollars")
    if normalization != "Absolute":
        if context is None:
            raise ValueError("Load country context before normalizing impacts")
        data = attach_event_context(data, context)
    columns = dimensions + ["Metric", "Value", "Events", "Reported", "Missing",
                            "Coverage (%)", "Eligible", "Missing context", "Denominator"]
    rows = []
    for keys, group in data.groupby(dimensions, dropna=False, observed=True, sort=True):
        keys = keys if isinstance(keys, tuple) else (keys,)
        events = len(group)
        for name in metrics:
            metric = METRICS[name]
            values = (pd.to_numeric(group[metric.column], errors="coerce") * metric.factor
                      if metric.column else pd.Series(1.0, index=group.index))
            reported = int(values.count())
            if normalization != "Absolute":
                baseline = ("Population" if normalization == "Per 100,000 residents"
                            else "GDP (current US$)")
                scale = 100000 if baseline == "Population" else 100
                values = values / group[baseline].where(group[baseline] > 0) * scale
            eligible = int(values.count())
            total = values.sum(min_count=1)
            divisor = eligible
            if name == "Events":
                value, divisor = total, eligible
            elif aggregation == "Total":
                value = total
            elif aggregation == "Median per event":
                value = values.median() if eligible else float("nan")
            else:
                divisor = events if denominator == "All events" else eligible
                value = total / divisor if divisor else float("nan")
            rows.append(dict(zip(dimensions, keys)) | {
                "Metric": name, "Value": value, "Events": events, "Reported": reported,
                "Missing": events - reported, "Coverage (%)": reported / events * 100,
                "Eligible": eligible, "Missing context": reported - eligible, "Denominator": divisor,
            })
    return pd.DataFrame(rows, columns=columns)
