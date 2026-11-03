"""Visualization module for AirAware Bengaluru.

Generates publication-quality static charts (Matplotlib, 300 DPI) and interactive
charts (Plotly) complying with assignment requirements:
1. Daily AQI line chart with category background bands (Required Chart #1).
2. Category count bar chart (Required Chart #2).
3. Particulate matter trends (PM2.5 and PM10) with Indian NAAQS and WHO 2021 limits.
4. Dominant pollutant frequency breakdown.
5. All figures contain explicit source provenance and access date footnotes.
"""

from pathlib import Path
from typing import Optional, Union
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from airaware.aqi import load_categories


def _get_aqi_column(df: pd.DataFrame) -> str:
    """Retrieve appropriate AQI column name."""
    if "aqi_derived" in df.columns:
        return "aqi_derived"
    return "aqi_reported"


def _get_provenance_footnote(df: pd.DataFrame) -> str:
    """Construct provenance footnote string from dataframe."""
    station = df["station"].iloc[0] if "station" in df.columns and len(df) > 0 else "BTM Layout, Bengaluru - CPCB"
    source = df["source"].iloc[0] if "source" in df.columns and len(df) > 0 else "CPCB CAAQMS"
    accessed = df["accessed_on"].iloc[0] if "accessed_on" in df.columns and len(df) > 0 else "2026-11-03"
    return f"Source: {source} | Station: {station} | Accessed: {accessed} | Quality-Controlled"


# ==========================================
# 1. Matplotlib Charts (300 DPI Export)
# ==========================================

def plot_daily_aqi_matplotlib(
    df: pd.DataFrame,
    output_path: Optional[Union[str, Path]] = None,
    dpi: int = 300,
) -> plt.Figure:
    """Plot daily AQI line chart with CPCB category background bands. (Required Chart #1)"""
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=dpi)

    aqi_col = _get_aqi_column(df)
    dates = pd.to_datetime(df["date"])
    aqi_values = df[aqi_col]

    # Category background bands
    bands = [
        (0, 50, "#e8f5e9", "Good (0–50)"),
        (51, 100, "#f1f8e9", "Satisfactory (51–100)"),
        (101, 200, "#fffde7", "Moderate (101–200)"),
        (201, 300, "#fff3e0", "Poor (201–300)"),
        (301, 400, "#fce4ec", "Very Poor (301–400)"),
        (401, 500, "#ede7f6", "Severe (401–500)"),
    ]

    max_val = aqi_values.max() if pd.notnull(aqi_values.max()) else 120
    max_plot_aqi = max(130, int(max_val) + 25)

    for y_lo, y_hi, bg_color, _ in bands:
        if y_lo <= max_plot_aqi:
            ax.axhspan(y_lo, min(y_hi, max_plot_aqi), color=bg_color, alpha=0.65, zorder=1)

    # Plot line and markers
    ax.plot(
        dates,
        aqi_values,
        marker="o",
        markersize=7,
        color="#1565c0",
        linewidth=2.2,
        label="Derived AQI (CPCB Formula)",
        zorder=3,
    )

    # Add data labels
    for d, val in zip(dates, aqi_values):
        if pd.notnull(val):
            ax.annotate(
                f"{int(round(val))}",
                xy=(d, val),
                xytext=(0, 7),
                textcoords="offset points",
                ha="center",
                fontsize=8.5,
                fontweight="bold",
                color="#0d47a1",
                zorder=4,
            )

    ax.set_ylim(0, max_plot_aqi)
    ax.set_title("Daily Air Quality Index (AQI) — 14-Day Observation (After QC)", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Date", fontsize=10, fontweight="bold")
    ax.set_ylabel("Air Quality Index (AQI)", fontsize=10, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.4, zorder=2)

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    fig.autofmt_xdate(rotation=35, ha="right")

    footnote = _get_provenance_footnote(df)
    plt.figtext(0.5, 0.01, footnote, wrap=True, horizontalalignment="center", fontsize=8, color="#555555", style="italic")

    plt.tight_layout(rect=[0, 0.04, 1, 1])

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_p, dpi=dpi)

    return fig


def plot_category_counts_matplotlib(
    cat_df: pd.DataFrame,
    df_raw_for_footnote: pd.DataFrame,
    output_path: Optional[Union[str, Path]] = None,
    dpi: int = 300,
) -> plt.Figure:
    """Plot bar chart of AQI category distributions. (Required Chart #2)"""
    fig, ax = plt.subplots(figsize=(9, 5), dpi=dpi)

    categories = cat_df["Category"].tolist()
    counts = cat_df["Count"].tolist()
    colors = cat_df["Color"].tolist()

    bars = ax.bar(categories, counts, color=colors, edgecolor="#424242", width=0.55, zorder=3)

    for bar in bars:
        h = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            h + 0.15,
            f"{int(h)} ({round(h / sum(counts) * 100, 1)}%)" if sum(counts) > 0 else f"{int(h)}",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
        )

    ax.set_ylim(0, max(counts) + 2.5 if counts else 10)
    ax.set_title("Frequency Distribution of CPCB AQI Categories (14 Days, After QC)", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("AQI Category", fontsize=10, fontweight="bold")
    ax.set_ylabel("Number of Days", fontsize=10, fontweight="bold")
    ax.grid(axis="y", linestyle="--", alpha=0.5, zorder=2)

    footnote = _get_provenance_footnote(df_raw_for_footnote)
    plt.figtext(0.5, 0.01, footnote, wrap=True, horizontalalignment="center", fontsize=8, color="#555555", style="italic")

    plt.tight_layout(rect=[0, 0.04, 1, 1])

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_p, dpi=dpi)

    return fig


def plot_pollutants_limits_matplotlib(
    df: pd.DataFrame,
    output_path: Optional[Union[str, Path]] = None,
    dpi: int = 300,
) -> plt.Figure:
    """Plot PM2.5 and PM10 concentrations against Indian NAAQS and WHO 2021 guidelines."""
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=dpi)

    dates = pd.to_datetime(df["date"])

    ax.plot(dates, df["pm25"], marker="s", color="#e65100", label="PM2.5 (24-h; Jan 8 unavailable)", linewidth=2.0, zorder=3)
    ax.plot(dates, df["pm10"], marker="^", color="#2e7d32", label="PM10 (24-h)", linewidth=2.0, zorder=3)

    # Standards reference lines
    ax.axhline(60, color="#d32f2f", linestyle="--", linewidth=1.5, label="NAAQS PM2.5 Limit (60 µg/m³)", zorder=2)
    ax.axhline(100, color="#1b5e20", linestyle="--", linewidth=1.5, label="NAAQS PM10 Limit (100 µg/m³)", zorder=2)
    ax.axhline(15, color="#f57c00", linestyle=":", linewidth=1.4, label="WHO 2021 PM2.5 Guideline (15 µg/m³)", zorder=2)
    ax.axhline(45, color="#388e3c", linestyle=":", linewidth=1.4, label="WHO 2021 PM10 Guideline (45 µg/m³)", zorder=2)

    ax.set_title("Particulate Concentrations (PM2.5 & PM10) vs. NAAQS & WHO Standards (After QC)", fontsize=12.5, fontweight="bold", pad=12)
    ax.set_xlabel("Date", fontsize=10, fontweight="bold")
    ax.set_ylabel("Concentration (µg/m³)", fontsize=10, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.4, zorder=1)

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    fig.autofmt_xdate(rotation=35, ha="right")

    ax.legend(loc="upper right", fontsize=8.5, framealpha=0.9)

    footnote = _get_provenance_footnote(df)
    plt.figtext(0.5, 0.01, footnote, wrap=True, horizontalalignment="center", fontsize=8, color="#555555", style="italic")

    plt.tight_layout(rect=[0, 0.04, 1, 1])

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_p, dpi=dpi)

    return fig


def plot_dominant_pollutant_matplotlib(
    df: pd.DataFrame,
    output_path: Optional[Union[str, Path]] = None,
    dpi: int = 300,
) -> plt.Figure:
    """Plot dominant pollutant breakdown as a clean donut chart."""
    fig, ax = plt.subplots(figsize=(7, 5), dpi=dpi)

    dom_col = "dominant_pm" if "dominant_pm" in df.columns else "prominent_pollutant"
    counts = df[dom_col].value_counts()
    colors = ["#4caf50" if "10" in str(k) else "#ff9800" for k in counts.index]

    wedges, texts, autotexts = ax.pie(
        counts.values,
        labels=counts.index,
        autopct="%1.1f%%",
        startangle=140,
        colors=colors,
        wedgeprops=dict(width=0.4, edgecolor="white", linewidth=2),
    )

    for at in autotexts:
        at.set_fontsize(10)
        at.set_fontweight("bold")

    ax.set_title("Dominant Particulate Pollutant Distribution (14 Days, After QC)", fontsize=12, fontweight="bold", pad=12)

    footnote = _get_provenance_footnote(df)
    plt.figtext(0.5, 0.01, footnote, wrap=True, horizontalalignment="center", fontsize=8, color="#555555", style="italic")

    plt.tight_layout(rect=[0, 0.04, 1, 1])

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_p, dpi=dpi)

    return fig


# ==========================================
# 2. Interactive Plotly Charts (for Streamlit)
# ==========================================

def plot_daily_aqi_plotly(df: pd.DataFrame) -> go.Figure:
    """Create interactive Plotly figure for daily AQI."""
    fig = go.Figure()
    aqi_col = _get_aqi_column(df)

    bands = [
        (0, 50, "rgba(46, 125, 50, 0.12)", "Good"),
        (51, 100, "rgba(85, 139, 47, 0.12)", "Satisfactory"),
        (101, 200, "rgba(245, 127, 23, 0.15)", "Moderate"),
        (201, 300, "rgba(230, 81, 0, 0.15)", "Poor"),
        (301, 400, "rgba(194, 24, 91, 0.15)", "Very Poor"),
        (401, 500, "rgba(74, 20, 140, 0.15)", "Severe"),
    ]

    max_aqi = max(130, int(df[aqi_col].max() + 25) if pd.notnull(df[aqi_col].max()) else 130)

    for y0, y1, col, name in bands:
        if y0 <= max_aqi:
            fig.add_hrect(
                y0=y0,
                y1=min(y1, max_aqi),
                fillcolor=col,
                layer="below",
                line_width=0,
                annotation_text=name,
                annotation_position="top left",
            )

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df[aqi_col],
            mode="lines+markers+text",
            name="Derived AQI",
            line=dict(color="#1565c0", width=3),
            marker=dict(size=9, color="#0d47a1"),
            text=df[aqi_col].apply(lambda v: str(int(round(v))) if pd.notnull(v) else ""),
            textposition="top center",
            hovertemplate="<b>Date:</b> %{x}<br><b>AQI:</b> %{y}<br><b>Category:</b> %{text}<extra></extra>",
        )
    )

    fig.update_layout(
        title="<b>Daily Air Quality Index (AQI) with CPCB Category Bands (After QC)</b>",
        xaxis_title="Date",
        yaxis_title="AQI",
        yaxis=dict(range=[0, max_aqi]),
        template="plotly_white",
        hovermode="x unified",
        margin=dict(l=40, r=40, t=50, b=40),
    )
    return fig


def plot_category_counts_plotly(cat_df: pd.DataFrame) -> go.Figure:
    """Create interactive Plotly bar chart for category frequency."""
    fig = go.Figure(
        go.Bar(
            x=cat_df["Category"],
            y=cat_df["Count"],
            marker_color=cat_df["Color"],
            text=cat_df.apply(lambda r: f"{r['Count']} ({r['Percentage']}%)", axis=1),
            textposition="auto",
        )
    )

    fig.update_layout(
        title="<b>AQI Category Frequency Distribution (14 Days, After QC)</b>",
        xaxis_title="Category",
        yaxis_title="Count of Days",
        template="plotly_white",
        margin=dict(l=40, r=40, t=50, b=40),
    )
    return fig


def plot_pollutants_limits_plotly(df: pd.DataFrame) -> go.Figure:
    """Create interactive Plotly chart for PM concentrations and regulatory thresholds."""
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(x=df["date"], y=df["pm25"], mode="lines+markers", name="PM2.5 (µg/m³; Jan 8 N/A)", line=dict(color="#e65100", width=2.5))
    )
    fig.add_trace(
        go.Scatter(x=df["date"], y=df["pm10"], mode="lines+markers", name="PM10 (µg/m³)", line=dict(color="#2e7d32", width=2.5))
    )

    # Standard thresholds
    fig.add_hline(y=60, line_dash="dash", line_color="#d32f2f", annotation_text="NAAQS PM2.5 (60 µg/m³)")
    fig.add_hline(y=100, line_dash="dash", line_color="#1b5e20", annotation_text="NAAQS PM10 (100 µg/m³)")
    fig.add_hline(y=15, line_dash="dot", line_color="#f57c00", annotation_text="WHO PM2.5 (15 µg/m³)")
    fig.add_hline(y=45, line_dash="dot", line_color="#388e3c", annotation_text="WHO PM10 (45 µg/m³)")

    fig.update_layout(
        title="<b>Particulate Matter Concentrations vs. NAAQS and WHO Limits (After QC)</b>",
        xaxis_title="Date",
        yaxis_title="Concentration (µg/m³)",
        template="plotly_white",
        hovermode="x unified",
        margin=dict(l=40, r=40, t=50, b=40),
    )
    return fig


def plot_dominant_pollutant_plotly(df: pd.DataFrame) -> go.Figure:
    """Create interactive Plotly donut chart of dominant pollutants."""
    dom_col = "dominant_pm" if "dominant_pm" in df.columns else "prominent_pollutant"
    counts = df[dom_col].value_counts().reset_index()
    counts.columns = ["Pollutant", "Days"]

    colors = ["#4caf50" if "10" in str(p) else "#ff9800" for p in counts["Pollutant"]]

    fig = px.pie(
        counts,
        names="Pollutant",
        values="Days",
        hole=0.45,
        title="<b>Dominant Particulate Pollutant Distribution (After QC)</b>",
        color_discrete_sequence=colors,
    )
    fig.update_traces(textinfo="label+percent+value")
    fig.update_layout(template="plotly_white", margin=dict(l=30, r=30, t=50, b=30))
    return fig
