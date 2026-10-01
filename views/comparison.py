import pandas as pd
import plotly.express as px
import streamlit as st

from utils.comparison import AGGREGATIONS, DENOMINATORS, METRICS, aggregate_impacts
from utils.filters import get_filter_period, get_filtered_data


def show_charts(summary, metrics, dimension, countries, aggregation):
    colors = dict(zip(countries, px.colors.qualitative.Safe * (len(countries) // 11 + 1)))
    for offset in range(0, len(metrics), 2):
        columns = st.columns(2)
        for column, metric in zip(columns, metrics[offset:offset + 2]):
            frame = summary[summary["Metric"] == metric]
            with column:
                st.subheader(metric)
                if frame.empty or frame["Value"].isna().all():
                    st.info("No reported values for this metric in the selection.")
                    continue
                unit = METRICS[metric].unit
                y_label = unit if metric == "Events" else f"{aggregation} ({unit})"
                kwargs = dict(color="Country", color_discrete_map=colors,
                              category_orders={"Country": countries},
                              hover_data=["Events", "Reported", "Missing", "Coverage (%)", "Denominator"],
                              labels={"Value": y_label})
                if dimension == "Start Year":
                    fig = px.line(frame, x=dimension, y="Value", markers=True, **kwargs)
                    fig.update_xaxes(dtick=1, tickformat="d")
                elif dimension == "Disaster Type":
                    fig = px.bar(frame, x="Value", y=dimension, orientation="h",
                                 barmode="group", **kwargs)
                else:
                    fig = px.bar(frame, x=dimension, y="Value", **kwargs)
                fig.update_layout(height=max(360, frame[dimension].nunique() * 32)
                                  if dimension == "Disaster Type" else 360,
                                  legend_title_text="", margin=dict(l=10, r=10, t=15, b=10))
                st.plotly_chart(fig, width="stretch", key=f"comparison.chart.{dimension}.{metric}")


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
    countries_available = sorted(data["Country"].dropna().unique())
    if "comparison.countries" in st.session_state:
        st.session_state["comparison.countries"] = [
            name for name in st.session_state["comparison.countries"] if name in countries_available
        ]
    countries = st.multiselect("Countries to compare", countries_available,
                               default=countries_available[:2], key="comparison.countries",
                               help="Choose any number of countries available after sidebar filters.")
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
    st.caption("Each EM-DAT row represents one disaster affecting one country. Missing impacts remain unavailable.")
    if aggregation == "Mean per event" and denominator == "All events":
        st.info("Observed impact ÷ all events. Unreported impacts can make this average lower than the true impact per event.")
    if aggregation == "Median per event":
        st.caption("Medians use reported values only. The Events measure always shows the event count.")

    summary = aggregate_impacts(selected, metrics, aggregation=aggregation, denominator=denominator)
    show_charts(summary, metrics, "Country", countries, aggregation)
    type_tab, trend_tab, coverage_tab = st.tabs(["By disaster type", "Annual trends", "Reporting coverage"])
    with type_tab:
        by_type = aggregate_impacts(selected, metrics, ["Country", "Disaster Type"], aggregation, denominator)
        show_charts(by_type, metrics, "Disaster Type", countries, aggregation)
    with trend_tab:
        annual = aggregate_impacts(selected, metrics, ["Country", "Start Year"], aggregation, denominator)
        show_charts(annual, metrics, "Start Year", countries, aggregation)
        st.caption("Years without records are omitted. Lines do not imply continuous observation.")
    with coverage_tab:
        st.dataframe(summary, hide_index=True, width="stretch")
        st.caption("Reported counts include explicit zeros. Blank values may mean no impact or unknown/unreported impact; they are not filled with zero.")
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
