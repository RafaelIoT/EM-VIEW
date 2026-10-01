import pandas as pd
import requests
import streamlit as st

from utils.comparison import AGGREGATIONS, DENOMINATORS, METRICS, aggregate_impacts
from utils.filters import get_filter_period, get_filtered_data
from utils.worldbank import fetch_country_indicators, country_snapshot
from utils.comparison_charts import PALETTES, country_colors, make_comparison_chart
from utils.comparison_exports import analysis_bundle, csv_bytes, summary_for_export


@st.cache_data(ttl=86400, show_spinner=False)
def load_country_context(codes, start_year, end_year):
    return fetch_country_indicators(codes, start_year, end_year)


def show_country_context(selected, reference_year):
    st.subheader("Population and economy")
    st.caption("World Bank annual population, GDP and GDP per capita. Values and source years are shown separately.")
    codes = tuple(sorted(selected["ISO"].dropna().unique()))
    first_year = min(int(selected["Start Year"].min()), reference_year - 5)
    if st.button("Load country context", key="comparison.load_context"):
        try:
            with st.spinner("Loading World Bank indicators…"):
                st.session_state["comparison.context"] = load_country_context(codes, first_year, reference_year)
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            st.warning(f"Country context is unavailable: {exc}. Absolute comparisons remain available.")
    context = st.session_state.get("comparison.context")
    if context is None:
        st.caption("Load country context to enable population-adjusted rates and economic comparisons.")
        return None
    scope = context.attrs
    if (not set(codes).issubset(scope.get("iso_codes", codes))
            or reference_year > scope.get("end_year", reference_year)
            or first_year < scope.get("start_year", first_year)):
        st.info("Load country context for the current countries and period.")
        return None
    country_names = selected[["Country", "ISO"]].drop_duplicates()
    snapshot = country_names.merge(country_snapshot(context, reference_year), how="left", on="ISO")
    st.dataframe(snapshot, hide_index=True, width="stretch", column_config={
        "Population": st.column_config.NumberColumn(format="%d"),
        "GDP (current US$)": st.column_config.NumberColumn(format="$%.0f"),
        "GDP per capita (current US$)": st.column_config.NumberColumn(format="$%.0f"),
        **{f"{name} year": st.column_config.NumberColumn(format="%d")
           for name in ("Population", "GDP (current US$)", "GDP per capita (current US$)")},
    })
    st.caption(f"Context reference: {reference_year}. Latest available value at or before that year. "
               f"Retrieved series: {scope.get('start_year', 'unavailable')}–{scope.get('end_year', 'unavailable')}. "
               f"World Bank updated: {scope.get('last_updated', 'unavailable')}. "
               f"Retrieved: {scope.get('retrieved_at', 'unavailable')}.")
    with st.expander("Annual country indicators and sources"):
        st.dataframe(context[context["ISO"].isin(codes)], hide_index=True, width="stretch")
        st.markdown("[Population](https://data.worldbank.org/indicator/SP.POP.TOTL) · "
                    "[GDP (current US$)](https://data.worldbank.org/indicator/NY.GDP.MKTP.CD) · "
                    "[GDP per capita](https://data.worldbank.org/indicator/NY.GDP.PCAP.CD)")
    return context


def show_charts(summary, metrics, dimension, countries, aggregation, normalization, settings, colors):
    for offset in range(0, len(metrics), 2):
        columns = st.columns(2)
        for column, metric in zip(columns, metrics[offset:offset + 2]):
            frame = summary[summary["Metric"] == metric]
            with column:
                st.subheader(metric)
                if frame.empty or frame["Value"].isna().all():
                    st.info("No reported values for this metric in the selection.")
                    continue
                fig = make_comparison_chart(frame, metric, dimension, countries, colors,
                                             aggregation, normalization, **settings)
                st.plotly_chart(fig, width="stretch", key=f"comparison.chart.{dimension}.{metric}")


def show_event_records(selected):
    search = st.text_input("Search event records", key="comparison.event_search",
                           help="Search event ID, name, location, country and disaster type.")
    records = selected
    if search:
        fields = [c for c in ["DisNo.", "Event Name", "Location", "Country", "Disaster Type"] if c in records]
        match = pd.Series(False, index=records.index)
        for field in fields:
            match |= records[field].fillna("").astype(str).str.contains(search, case=False, regex=False)
        records = records[match]
    defaults = [c for c in ["DisNo.", "Country", "Disaster Type", "Disaster Subtype", "Event Name",
                            "Start Year", "Start Month", "Start Day", "Total Deaths", "Total Affected"] if c in selected]
    if "comparison.event_columns" in st.session_state:
        st.session_state["comparison.event_columns"] = [c for c in st.session_state["comparison.event_columns"] if c in selected]
    columns = st.multiselect("Event columns", selected.columns.tolist(), default=defaults,
                             key="comparison.event_columns")
    st.caption(f"{len(records):,} matching records. Event-table search only filters this table. "
               "Source damage columns retain their thousands-of-US$ units.")
    if columns:
        st.dataframe(records[columns], hide_index=True, width="stretch")
        st.download_button("Download displayed records (CSV)", csv_bytes(records[columns]),
                            file_name="emview_event_records.csv", mime="text/csv", key="comparison.export_events")
    else:
        st.info("Choose at least one event column.")


def main():
    st.session_state["page"] = "comparison"
    st.header("Compare country impacts")
    if "data" not in st.session_state:
        st.info("Load an EM-DAT workbook on Home to compare countries.")
        return
    data = get_filtered_data()
    if data.empty:
        st.info("No events match these filters. Widen the period or reset the filters.")
        return

    start, end = get_filter_period()
    st.caption(f"{start:%d %b %Y} – {end:%d %b %Y} · {len(data):,} records after sidebar filters")
    countries = sorted(data["Country"].dropna().unique())
    st.caption("Choose countries with the sidebar checkboxes. This selection applies to every view.")
    controls = st.columns([2, 1, 1])
    available_metrics = [name for name, metric in METRICS.items()
                         if metric.column is None or metric.column in data]
    if "comparison.metrics" in st.session_state:
        st.session_state["comparison.metrics"] = [
            name for name in st.session_state["comparison.metrics"] if name in available_metrics
        ]
    metrics = controls[0].multiselect("Impact measures", available_metrics,
                                      default=["Deaths", "Affected people"], key="comparison.metrics")
    aggregation = controls[1].selectbox("Aggregation", AGGREGATIONS, key="comparison.aggregation")
    denominator = controls[2].selectbox("Average denominator", DENOMINATORS,
                                        disabled=aggregation != "Mean per event",
                                        key="comparison.denominator")
    if not countries or not metrics:
        st.info("Select at least one country and one impact measure.")
        return
    selected = data[data["Country"].isin(countries)]
    stats = st.columns(4)
    stats[0].metric("Events in selection", f"{len(selected):,}")
    stats[1].metric("Countries", len(countries))
    for column, label, field in [(stats[2], "Reported deaths", "Total Deaths"),
                                  (stats[3], "Reported affected", "Total Affected")]:
        value = selected[field].sum(min_count=1) if field in selected else float("nan")
        column.metric(label, "Unavailable" if pd.isna(value) else f"{value:,.0f}")
    with st.expander("Population and GDP context"):
        context = show_country_context(selected, end.year)
    normalization_options = ["Absolute"]
    if context is not None:
        normalization_options.append("Per 100,000 residents")
        if metrics == ["Damage (current US$)"]:
            normalization_options.append("% of event-year GDP")
    if st.session_state.get("comparison.normalization", "Absolute") not in normalization_options:
        st.session_state["comparison.normalization"] = "Absolute"
    normalization = st.selectbox("Normalization", normalization_options, key="comparison.normalization")
    with st.expander("Customize charts"):
        chart_controls = st.columns(3)
        orientation = chart_controls[0].selectbox("Country bars", ["Vertical", "Horizontal"], key="comparison.orientation")
        order = chart_controls[1].selectbox("Category order", ["Alphabetical", "Highest impact"], key="comparison.order")
        palette = chart_controls[2].selectbox("Country colors", list(PALETTES), key="comparison.palette")
        log_scale = st.checkbox("Logarithmic impact scale", key="comparison.log_scale")
        value_labels = st.checkbox("Show bar values", key="comparison.value_labels")
    chart_settings = dict(orientation=orientation, order=order, log_scale=log_scale, value_labels=value_labels)
    colors = country_colors(st.session_state["data"]["Country"].dropna().unique().tolist(), palette)
    if log_scale:
        st.caption("A logarithmic scale displays positive values only; zeros and missing values remain in the reporting table.")
    if normalization != "Absolute":
        st.caption("Rates use each event's country population or GDP in its start year. "
                   "Missing annual denominators exclude that reported impact from the rate; "
                   "the reporting table shows exclusions. Context-table fallback years are not used.")
        st.caption("Period totals sum event-year rates across events and years. They are cumulative impacts, "
                   "not a unique-person percentage or a share of the period's GDP.")
    st.caption("Each EM-DAT row represents one disaster affecting one country. Missing impacts remain unavailable.")
    if aggregation == "Mean per event" and denominator == "All events":
        st.info("Observed impact ÷ all events. Unreported impacts can make this average lower than the true impact per event.")
    if aggregation == "Median per event":
        st.caption("Medians use reported values only. The Events measure always shows the event count.")

    summary = aggregate_impacts(selected, metrics, aggregation=aggregation, denominator=denominator,
                                normalization=normalization, context=context)
    export_units = {metric: ("% of event-year GDP" if normalization == "% of event-year GDP" else
                             METRICS[metric].unit + (" per 100,000 residents" if normalization != "Absolute" else ""))
                    for metric in metrics}
    export_settings = dict(start_date=start.isoformat(), end_date=end.isoformat(), aggregation=aggregation,
                           normalization=normalization, average_denominator=denominator, units=export_units)
    if summary["Missing context"].sum():
        st.warning("Some reported impacts lack a matching annual denominator. See Missing context in the reporting table.")
    if "Events" in metrics:
        st.caption("Events shows the total event count, or the cumulative event rate when population-adjusted, regardless of the impact aggregation.")
    show_charts(summary, metrics, "Country", countries, aggregation, normalization, chart_settings, colors)
    type_tab, trend_tab, coverage_tab, events_tab = st.tabs(["By disaster type", "Annual trends", "Reporting coverage", "Event records"])
    with type_tab:
        by_type = aggregate_impacts(selected, metrics, ["Country", "Disaster Type"], aggregation,
                                    denominator, normalization, context)
        show_charts(by_type, metrics, "Disaster Type", countries, aggregation, normalization, chart_settings, colors)
    with trend_tab:
        annual = aggregate_impacts(selected, metrics, ["Country", "Start Year"], aggregation,
                                   denominator, normalization, context)
        show_charts(annual, metrics, "Start Year", countries, aggregation, normalization, chart_settings, colors)
        st.caption("Years without records appear as gaps; no impacts are imputed for those years.")
    with coverage_tab:
        st.dataframe(summary, hide_index=True, width="stretch")
        st.caption("Reported counts include explicit zeros. Blank values may mean no impact or unknown/unreported impact; they are not filled with zero.")
        st.download_button("Download country summary (CSV)", csv_bytes(summary_for_export(summary, export_settings)),
                            file_name="emview_country_summary.csv", mime="text/csv", key="comparison.export_summary")
    with events_tab:
        show_event_records(selected)
    settings = dict(
        source_file=st.session_state.get("filename"), start_date=start.isoformat(), end_date=end.isoformat(),
        date_match=st.session_state.get("filter.date_match", "starts"),
        include_partial_start_dates=st.session_state.get("filter.include_partial", True),
        classification_key=st.session_state["filter.classification_key"],
        region=st.session_state["filter.region"], subregion=st.session_state["filter.subregion"],
        sidebar_countries=st.session_state["filter.countries"],
        disaster_groups=st.session_state.get("filter.groups", []), disaster_types=st.session_state.get("filter.types", []),
        disaster_subgroups=st.session_state.get("filter.subgroups", []), disaster_subtypes=st.session_state.get("filter.subtypes", []),
        require_reported_measures=st.session_state.get("filter.reported", []),
        minimum_deaths=st.session_state.get("filter.minimum_deaths", 0),
        minimum_affected=st.session_state.get("filter.minimum_affected", 0),
        event_search=st.session_state.get("filter.event_search", ""),
        countries=countries, metrics=metrics, aggregation=aggregation, average_denominator=denominator,
        normalization=normalization, chart_settings=chart_settings | {"palette": palette},
        units=export_units,
        emdat_source="EM-DAT, CRED / UCLouvain, Brussels, Belgium; https://www.emdat.be",
        world_bank_source=None if context is None else context.attrs,
    )
    tables = {"country_summary": summary_for_export(summary, settings),
              "by_disaster_type": summary_for_export(by_type, settings),
              "annual_trends": summary_for_export(annual, settings), "filtered_events": selected}
    if context is not None:
        tables["annual_country_indicators"] = context[context["ISO"].isin(selected["ISO"].unique())]
    st.download_button("Download full analysis (ZIP)", analysis_bundle(tables, settings),
                        file_name="emview_comparison.zip", mime="application/zip", key="comparison.export_bundle",
                        help="Includes country/type/year summaries, analyzed events, annual country indicators and active settings.")
    with st.expander("How to interpret these comparisons"):
        st.markdown("""
        - **Total** sums reported impacts in the selected period.
        - **Mean per event** divides reported impact by the selected event denominator.
        - **Median per event** is the middle reported impact, less sensitive to very large disasters.
        - **Affected people** includes injured, affected and homeless people. Totals across events may count the same person more than once.
        - **Damage** is displayed in US dollars, converted from EM-DAT's thousands of US dollars. Current and inflation-adjusted damage are separate measures.

        Source: EM-DAT, CRED / UCLouvain, Brussels, Belgium. See the
        [EM-DAT public table definitions](https://doc.emdat.be/docs/data-structure-and-content/emdat-public-table/).
        """)


main()
