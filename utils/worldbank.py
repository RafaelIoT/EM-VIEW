"""World Bank WDI indicators, with exact country/year joins for impact rates."""
from datetime import datetime, timezone
import re

import pandas as pd
import requests


API_URL = "https://api.worldbank.org/v2"
INDICATORS = {
    "SP.POP.TOTL": "Population",
    "NY.GDP.MKTP.CD": "GDP (current US$)",
    "NY.GDP.PCAP.CD": "GDP per capita (current US$)",
}
CONTEXT_COLUMNS = ["ISO", "Year", *INDICATORS.values()]


def fetch_country_indicators(iso_codes: tuple[str, ...], start_year: int,
                             end_year: int) -> pd.DataFrame:
    """Fetch all pages of annual WDI data; unavailable values remain missing."""
    codes = sorted(set(iso_codes))
    if not codes:
        return pd.DataFrame(columns=CONTEXT_COLUMNS)
    if any(not re.fullmatch(r"[A-Z]{3}", code) for code in codes):
        raise ValueError("World Bank country codes must be three uppercase letters")
    if start_year > end_year:
        raise ValueError("Start year must not exceed end year")
    url = f"{API_URL}/country/{';'.join(codes)}/indicator/{';'.join(INDICATORS)}"
    # Preserve the API's literal range separator. Percent-encoded colons can
    # take a different, slow path through the World Bank API's cache/proxy.
    query_url = f"{url}?source=2&date={int(start_year)}:{int(end_year)}&format=json&per_page=1000"
    observations = {}
    page, pages, updated = 1, 1, None
    while page <= pages:
        page_url = query_url if page == 1 else f"{query_url}&page={page}"
        response = requests.get(page_url, timeout=(5, 30))
        response.raise_for_status()
        payload = response.json()
        if (not isinstance(payload, list) or len(payload) != 2
                or not isinstance(payload[0], dict)):
            raise ValueError("World Bank did not return an indicator dataset")
        pages = int(payload[0].get("pages", 1))
        if not 0 <= pages <= 100:
            raise ValueError("Unexpected World Bank pagination")
        updated = payload[0].get("lastupdated", updated)
        records = payload[1] or []
        if not isinstance(records, list):
            raise ValueError("World Bank returned invalid observations")
        for record in records:
            iso, year = record["countryiso3code"], int(record["date"])
            indicator = record["indicator"]["id"]
            if iso not in codes or indicator not in INDICATORS:
                continue
            observations.setdefault((iso, year), {})[INDICATORS[indicator]] = record["value"]
        page += 1
    rows = [dict(ISO=iso, Year=year) | values for (iso, year), values in observations.items()]
    result = pd.DataFrame(rows).reindex(columns=CONTEXT_COLUMNS)
    for column in INDICATORS.values():
        result[column] = pd.to_numeric(result[column], errors="coerce")
    result.attrs = {"source_url": query_url, "last_updated": updated,
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "start_year": start_year, "end_year": end_year, "iso_codes": codes}
    return result.sort_values(["ISO", "Year"]).reset_index(drop=True)


def country_snapshot(context: pd.DataFrame, reference_year: int) -> pd.DataFrame:
    """Latest reported value at/before the reference year, with each source year.

    This display-only fallback is never used for event-year normalizations.
    """
    rows = []
    for iso, group in context.groupby("ISO", sort=True):
        row = {"ISO": iso}
        past = group[group["Year"] <= reference_year].sort_values("Year")
        for indicator in INDICATORS.values():
            available = past.dropna(subset=[indicator])
            row[indicator] = available[indicator].iloc[-1] if len(available) else float("nan")
            row[f"{indicator} year"] = int(available["Year"].iloc[-1]) if len(available) else None
        rows.append(row)
    columns = ["ISO"] + [c for name in INDICATORS.values() for c in (name, f"{name} year")]
    return pd.DataFrame(rows, columns=columns)


def attach_event_context(data: pd.DataFrame, context: pd.DataFrame) -> pd.DataFrame:
    """Join annual denominators on ISO and event start year, with no gap filling."""
    return data.merge(
        context[CONTEXT_COLUMNS].rename(columns={"Year": "Start Year"}),
        how="left", on=["ISO", "Start Year"], validate="many_to_one",
    )
