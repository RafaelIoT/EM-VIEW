"""Optional source-category, reporting and event-severity filters."""
import pandas as pd


def filter_event_details(data, subgroups=(), subtypes=(), required_columns=(),
                         minimum_deaths=0, minimum_affected=0, search=""):
    result = data
    for column, choices in [("Disaster Subgroup", subgroups), ("Disaster Subtype", subtypes)]:
        if choices:
            result = result[result[column].isin(choices)]
    for column in required_columns:
        result = result[pd.to_numeric(result[column], errors="coerce").notna()]
    for column, minimum in [("Total Deaths", minimum_deaths), ("Total Affected", minimum_affected)]:
        if minimum > 0:
            result = result[pd.to_numeric(result[column], errors="coerce") >= minimum]
    if search.strip():
        match = pd.Series(False, index=result.index)
        for column in ["DisNo.", "Event Name", "Location", "Country", "Disaster Type", "Disaster Subtype"]:
            if column in result:
                match |= result[column].fillna("").astype(str).str.contains(search.strip(), case=False, regex=False)
        result = result[match]
    return result
