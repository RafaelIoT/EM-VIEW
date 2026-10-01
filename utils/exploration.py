"""Hazard profiles and rankings that preserve reporting uncertainty."""
import pandas as pd
import plotly.graph_objects as go

from utils.comparison import METRICS


def make_hazard_heatmap(summary, hazard="Disaster Type", display="Impact value"):
    frame = summary.copy()
    value = "Value"
    if display == "Share of country total (%)":
        total = frame.groupby("Country")["Value"].transform(lambda values: values.sum(min_count=1))
        frame["Share (%)"] = frame["Value"] / total.where(total > 0) * 100
        value = "Share (%)"
    elif display == "Reporting coverage (%)":
        value = "Coverage (%)"
    countries = sorted(frame["Country"].unique())
    hazards = sorted(frame[hazard].unique())
    index = pd.MultiIndex.from_product([countries, hazards], names=["Country", hazard])
    matrix = frame.set_index(["Country", hazard]).reindex(index)
    z = matrix[value].to_numpy().reshape(len(countries), len(hazards))
    details = matrix[["Events", "Reported", "Coverage (%)"]].to_numpy().reshape(len(countries), len(hazards), 3)
    fig = go.Figure(go.Heatmap(z=z, x=hazards, y=countries, customdata=details,
                              colorscale="Blues", zmin=0, hoverongaps=False,
                              colorbar=dict(title=display),
                              hovertemplate="%{y} · %{x}<br>Value: %{z:,.3g}<br>Events: %{customdata[0]}<br>Reported: %{customdata[1]}<br>Coverage: %{customdata[2]:.1f}%<extra></extra>"))
    fig.update_layout(height=max(400, 36 * len(countries) + 180), margin=dict(t=30, b=60))
    fig.update_yaxes(autorange="reversed", title="Country")
    fig.update_xaxes(title=hazard)
    return fig


def rank_events(data, metric, limit=10):
    spec = METRICS[metric]
    if spec.column is None:
        raise ValueError("Event rankings require an impact measure")
    result = data.copy()
    label = f"{metric} ({spec.unit})"
    result[label] = pd.to_numeric(result[spec.column], errors="coerce") * spec.factor
    result = result[result[label].notna()].sort_values(label, ascending=False, kind="stable").head(limit)
    result.insert(0, "Rank", range(1, len(result) + 1))
    columns = ["Rank", "DisNo.", "Country", "Disaster Type", "Disaster Subtype", "Start Year", label, "Event Name", "Location"]
    return result[[column for column in columns if column in result]].reset_index(drop=True)

