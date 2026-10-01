import pandas as pd
import plotly.express as px
import streamlit as st

from utils.comparison import AGGREGATIONS, DENOMINATORS, METRICS, aggregate_impacts
from utils.comparison_charts import country_colors
from utils.comparison_exports import csv_bytes, summary_for_export
from utils.exploration import make_hazard_heatmap, rank_events
from utils.filters import get_filter_period, get_filtered_data


def main():
    st.session_state["page"] = "explore"
    st.header("Explore disaster impacts")
    if "data" not in st.session_state:
        st.info("Load an EM-DAT workbook on Home to explore impacts.")
        return
    data = get_filtered_data()
    if data.empty:
        st.info("No events match these filters. Widen the period or reset the filters.")
        return
    start, end = get_filter_period()
    st.caption(f"{start:%d %b %Y} – {end:%d %b %Y} · {len(data):,} records · All views use the sidebar filters and country checkboxes.")
    measures = [name for name, spec in METRICS.items() if spec.column is None or spec.column in data]
    if st.session_state.get("explore.metric", "Deaths") not in measures:
        st.session_state["explore.metric"] = measures[0]
    metric = st.selectbox("Impact measure", measures, index=measures.index("Deaths") if "Deaths" in measures else 0, key="explore.metric")
    profile_tab, severity_tab, ranking_tab = st.tabs(["Hazard profile", "Frequency and severity", "Largest events"])
    with profile_tab:
        cols = st.columns(3)
        hazards = [column for column in ["Disaster Type", "Disaster Subtype", "Disaster Subgroup"] if column in data]
        hazard = cols[0].selectbox("Hazard level", hazards, key="explore.hazard")
        aggregation = cols[1].selectbox("Profile aggregation", AGGREGATIONS, key="explore.aggregation")
        displays = ["Impact value", "Reporting coverage (%)"]
        if aggregation == "Total" or metric == "Events":
            displays.insert(1, "Share of country total (%)")
        if st.session_state.get("explore.display", displays[0]) not in displays:
            st.session_state["explore.display"] = displays[0]
        display = cols[2].selectbox("Heatmap shows", displays, key="explore.display")
        profile_data = data.copy()
        profile_data[hazard] = profile_data[hazard].fillna("Unspecified")
        profile = aggregate_impacts(profile_data, [metric], ["Country", hazard], aggregation)
        st.plotly_chart(make_hazard_heatmap(profile, hazard, display), width="stretch", key="explore.profile")
        st.caption(f"{metric} · {aggregation} · {METRICS[metric].unit}. Means and medians use reported events. "
                   "Blank cells mean no records or no reported impact. A reported zero remains zero. Shares are unavailable when the country total is zero.")
        with st.expander("Profile values and reporting coverage"):
            st.dataframe(profile, hide_index=True, width="stretch")
            settings = dict(start_date=start.isoformat(), end_date=end.isoformat(), aggregation=aggregation,
                            average_denominator="Reported events", normalization="Absolute", units={metric: METRICS[metric].unit})
            st.download_button("Download hazard profile (CSV)", csv_bytes(summary_for_export(profile, settings)),
                                file_name="emview_hazard_profile.csv", mime="text/csv", key="explore.export_profile")
    with severity_tab:
        if metric == "Events":
            st.info("Choose an impact measure such as deaths or affected people to compare frequency and severity.")
        else:
            cols = st.columns(3)
            split = cols[0].checkbox("Split by disaster type", value=True, key="explore.split")
            statistic = cols[1].selectbox("Severity statistic", ["Mean per event", "Median per event"], key="explore.severity")
            denominator = cols[2].selectbox("Average denominator", DENOMINATORS, key="explore.denominator", disabled=statistic != "Mean per event")
            cols = st.columns(2)
            log_x = cols[0].checkbox("Logarithmic event count", key="explore.log_x")
            log_y = cols[1].checkbox("Logarithmic severity", key="explore.log_y")
            dimensions = ["Country"] + (["Disaster Type"] if split else [])
            severity = aggregate_impacts(data, [metric], dimensions, statistic, denominator)
            available = severity[severity["Value"].notna()]
            if available.empty:
                st.info("No reported values for this impact measure in the selection.")
            else:
                colors = country_colors(st.session_state["data"]["Country"].dropna().unique().tolist(), "Accessible")
                fig = px.scatter(available, x="Events", y="Value", color="Country", color_discrete_map=colors,
                                  hover_data=(["Disaster Type"] if split else []) + ["Reported", "Missing", "Coverage (%)", "Denominator"],
                                  labels={"Events": "Event count", "Value": f"{statistic} ({METRICS[metric].unit})"},
                                  log_x=log_x, log_y=log_y)
                fig.update_traces(marker=dict(size=13, line=dict(width=1, color="white")))
                fig.update_layout(height=480)
                st.plotly_chart(fig, width="stretch", key="explore.severity_chart")
            st.caption("Each point compares the number of country-disaster records with their impact per event. "
                       "Hover to inspect reporting coverage. Log scales display positive values only.")
            if statistic == "Mean per event" and denominator == "All events":
                st.info("Observed impact ÷ all events. Unreported impacts can lower this average.")
            with st.expander("Frequency and severity values"):
                st.dataframe(severity, hide_index=True, width="stretch")
    with ranking_tab:
        if metric == "Events":
            st.info("Choose an impact measure to rank events.")
        else:
            limit = st.slider("Number of events", min_value=5, max_value=50, value=10, step=5, key="explore.limit")
            ranked = rank_events(data, metric, limit)
            values = pd.to_numeric(data[METRICS[metric].column], errors="coerce")
            st.caption(f"Top {len(ranked)} country-disaster records by {metric.lower()}. {values.isna().sum():,} records with unreported values are excluded. "
                       "A disaster spanning countries can appear as more than one record.")
            if ranked.empty:
                st.info("No reported values to rank.")
            else:
                st.dataframe(ranked, hide_index=True, width="stretch")
                st.download_button("Download ranked events (CSV)", csv_bytes(ranked),
                                    file_name="emview_ranked_events.csv", mime="text/csv", key="explore.export_ranked")


main()
