"""Portable CSV analysis bundles with settings, units and source provenance."""
import io
import json
import zipfile

import pandas as pd


def csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8-sig")


def summary_for_export(frame: pd.DataFrame, settings: dict) -> pd.DataFrame:
    """Make standalone summaries interpretable outside the dashboard."""
    result = frame.copy()
    result["Unit"] = result["Metric"].map(settings["units"])
    for key, label in [("start_date", "Start date"), ("end_date", "End date"),
                       ("aggregation", "Aggregation"), ("normalization", "Normalization"),
                       ("average_denominator", "Average denominator")]:
        result[label] = settings[key]
    return result


def analysis_bundle(tables: dict[str, pd.DataFrame], settings: dict) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, frame in tables.items():
            archive.writestr(f"{name}.csv", csv_bytes(frame))
        archive.writestr("analysis.json", json.dumps(settings, ensure_ascii=False, indent=2,
                                                     allow_nan=False, default=str))
        archive.writestr("README.txt", (
            "EM-VIEW country comparison export\n\n"
            "analysis.json records the active filters, metric units, aggregation, "
            "normalization and sources. CSV blanks represent unavailable values, not zero.\n"
            "Reported counts include explicit zero values. Eligible counts show the values "
            "used after matching any annual country denominators.\n"
            "filtered_events.csv contains every source column for the analyzed country selection. "
            "Damage columns in this raw table retain EM-DAT's thousands-of-US$ units; "
            "damage Values in the summary tables are in US$.\n"
            "Country context display fallbacks are not used to normalize impacts. "
            "Multi-year normalized totals sum event-year ratios.\n\n"
            "EM-DAT, CRED / UCLouvain, Brussels, Belgium; https://www.emdat.be\n"
            "World Bank World Development Indicators; https://data.worldbank.org\n"
        ))
    return output.getvalue()
