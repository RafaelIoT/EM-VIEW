"""Plotly charts shared by all country comparison breakdowns."""
import pandas as pd
import plotly.express as px

from utils.comparison import METRICS


PALETTES = {
    "Accessible": px.colors.qualitative.Safe,
    "Plotly": px.colors.qualitative.Plotly,
    "Dark": px.colors.qualitative.Dark24,
}


def country_colors(countries: list[str], palette: str) -> dict[str, str]:
    """Assign stable colors from the full dataset's sorted country list."""
    colors = PALETTES[palette]
    return {name: colors[index % len(colors)] for index, name in enumerate(sorted(countries))}


def make_comparison_chart(frame: pd.DataFrame, metric: str, dimension: str,
                          countries: list[str], colors: dict[str, str],
                          aggregation: str, normalization: str = "Absolute",
                          orientation: str = "Vertical", order: str = "Alphabetical",
                          log_scale: bool = False, value_labels: bool = False):
    frame = frame.copy()
    unit = METRICS[metric].unit
    value_label = unit if metric == "Events" else f"{aggregation} ({unit})"
    if normalization == "Per 100,000 residents":
        value_label += " per 100,000 residents"
    elif normalization == "% of event-year GDP":
        value_label = f"{aggregation} (% of event-year GDP)"
    hover = ["Events", "Reported", "Missing", "Coverage (%)", "Eligible", "Missing context", "Denominator"]
    categories = sorted(frame[dimension].dropna().unique())
    if order == "Highest impact" and dimension != "Start Year":
        categories = frame.groupby(dimension)["Value"].sum(min_count=1).sort_values(ascending=False).index.tolist()
    kwargs = dict(color="Country", color_discrete_map=colors,
                  category_orders={"Country": countries, dimension: categories},
                  hover_data=hover, labels={"Value": value_label})
    horizontal = dimension == "Disaster Type" or (dimension == "Country" and orientation == "Horizontal")
    if dimension == "Start Year":
        # Insert absent years so Plotly cannot draw through observation gaps.
        first, last = int(frame[dimension].min()), int(frame[dimension].max())
        index = pd.MultiIndex.from_product([countries, range(first, last + 1)], names=["Country", dimension])
        frame = frame.set_index(["Country", dimension]).reindex(index).reset_index()
        fig = px.line(frame, x=dimension, y="Value", markers=True, **kwargs)
        fig.update_traces(connectgaps=False)
        fig.update_xaxes(dtick=1, tickformat="d")
    elif horizontal:
        fig = px.bar(frame, x="Value", y=dimension, orientation="h", barmode="group",
                     text_auto=".3s" if value_labels else False, **kwargs)
        fig.update_yaxes(categoryorder="array", categoryarray=categories, autorange="reversed")
    else:
        fig = px.bar(frame, x=dimension, y="Value", text_auto=".3s" if value_labels else False, **kwargs)
    if log_scale:
        if horizontal:
            fig.update_xaxes(type="log")
        else:
            fig.update_yaxes(type="log")
    height = max(360, len(categories) * max(40, 16 * len(countries))) if horizontal else 360
    fig.update_layout(height=height, legend_title_text="", margin=dict(l=10, r=10, t=15, b=10))
    return fig
