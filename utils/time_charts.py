"""Comparable annual charts; absent observations remain gaps."""
from math import ceil

import pandas as pd
import plotly.express as px

from utils.comparison import METRICS
from utils.comparison_charts import country_colors


def make_time_chart(summary, metric, dimension, aggregation,
                    style="Side-by-side bars", palette="Accessible",
                    countries=None, log_scale=False, value_labels=False):
    frame = summary.copy()
    if dimension:
        frame["Series"] = frame[dimension].fillna("Unspecified").astype(str)
    else:
        frame["Series"] = "All events"
    series = sorted(frame["Series"].unique())
    years = list(range(int(frame["Start Year"].min()), int(frame["Start Year"].max()) + 1))
    index = pd.MultiIndex.from_product([series, years], names=["Series", "Start Year"])
    frame = frame.set_index(["Series", "Start Year"]).reindex(index).reset_index()
    unit = METRICS[metric].unit
    value_label = unit if metric == "Events" else f"{aggregation} ({unit})"
    kwargs = dict(x="Start Year", y="Value", color="Series",
                  color_discrete_map=country_colors(countries or series, palette),
                  category_orders={"Series": series}, labels={"Value": value_label},
                  hover_data=["Events", "Reported", "Missing", "Coverage (%)", "Denominator"])
    if style == "Lines":
        fig = px.line(frame, markers=True, **kwargs)
        fig.update_traces(connectgaps=False)
        fig.update_xaxes(dtick=1, tickformat="d")
    else:
        frame["Start Year"] = frame["Start Year"].astype(str)
        kwargs["category_orders"]["Start Year"] = [str(year) for year in years]
        facet = {"facet_col": "Series", "facet_col_wrap": 2} if style == "Separate panels" else {}
        fig = px.bar(frame, barmode="group", text_auto=".3s" if value_labels else False,
                     **kwargs, **facet)
        fig.update_xaxes(type="category")
    if log_scale:
        fig.update_yaxes(type="log")
    fig.update_layout(legend_title_text=dimension or "Selection", margin=dict(t=35, b=35),
                      height=max(440, ceil(len(series) / 2) * 250) if style == "Separate panels" else 500)
    return fig
