import streamlit as st

from utils.comparison import AGGREGATIONS, DENOMINATORS, METRICS, aggregate_impacts
from utils.comparison_charts import PALETTES
from utils.comparison_exports import csv_bytes, summary_for_export
from utils.filters import get_filtered_data, get_filter_period
from utils.layout import PAGE_HELP_TEXT
from utils.time_charts import make_time_chart


def main():
    st.session_state["page"] = "time"
    st.header("Compare impacts over time")
    if "data" not in st.session_state:
        st.info("Load an EM-DAT workbook on Home to compare annual impacts.")
        return
    data = get_filtered_data()
    if data.empty:
        st.info("No events match these filters. Widen the period or reset the filters.")
        return
    start, end = get_filter_period()
    st.caption(f"{start:%d %b %Y} – {end:%d %b %Y} · {len(data):,} records · Choose countries with the sidebar checkboxes.")
    measures = [name for name, spec in METRICS.items() if spec.column is None or spec.column in data]
    dimensions = [name for name in ["Country", "Disaster Type", "Disaster Subtype", "Region", "Subregion"] if name in data] + ["All events"]
    cols = st.columns(3)
    metric = cols[0].selectbox("Impact measure", measures, index=measures.index("Deaths") if "Deaths" in measures else 0, key="time.metric")
    compare_by = cols[1].selectbox("Compare by", dimensions, key="time.dimension")
    style = cols[2].selectbox("Chart style", ["Side-by-side bars", "Lines", "Separate panels"], key="time.style")
    cols = st.columns(3)
    aggregation = cols[0].selectbox("Aggregation", AGGREGATIONS, key="time.aggregation")
    denominator = cols[1].selectbox("Average denominator", DENOMINATORS, key="time.denominator",
                                    disabled=aggregation != "Mean per event" or metric == "Events")
    palette = cols[2].selectbox("Colors", list(PALETTES), key="time.palette")
    with st.expander("Chart options"):
        log_scale = st.checkbox("Logarithmic impact scale", key="time.log_scale")
        value_labels = st.checkbox("Show bar values", key="time.value_labels")
    dimension = None if compare_by == "All events" else compare_by
    summary = aggregate_impacts(data, [metric], ["Start Year"] + ([dimension] if dimension else []), aggregation, denominator)
    if summary["Value"].isna().all():
        st.info("No reported values for this impact measure in the selection.")
    else:
        countries = st.session_state["data"]["Country"].dropna().unique().tolist() if dimension == "Country" else None
        fig = make_time_chart(summary, metric, dimension, aggregation, style, palette, countries, log_scale, value_labels)
        st.plotly_chart(fig, width="stretch", key="time.chart")
    st.caption("Years use event start dates. Missing impacts and years without records remain gaps; explicit zeros are reported values.")
    if metric == "Events":
        st.caption("Events always shows the annual country-disaster record count, regardless of aggregation.")
    elif aggregation == "Mean per event" and denominator == "All events":
        st.info("Observed impact ÷ all events. Unreported impacts can lower this average.")
    if log_scale:
        st.caption("The logarithmic scale displays positive values only. Zeros remain in the annual summary.")
    with st.expander("Annual summary and reporting coverage"):
        st.dataframe(summary, hide_index=True, width="stretch")
        settings = dict(start_date=start.isoformat(), end_date=end.isoformat(), aggregation=aggregation,
                        average_denominator=denominator, normalization="Absolute", units={metric: METRICS[metric].unit})
        st.download_button("Download annual summary (CSV)", csv_bytes(summary_for_export(summary, settings)),
                            file_name="emview_annual_summary.csv", mime="text/csv", key="time.export")
    with st.expander("See page details", icon=":material/info:"):
        st.markdown(PAGE_HELP_TEXT["time"])


main()
