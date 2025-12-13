import plotly.graph_objects as go
import pandas as pd
import numpy as np

# --------------------------------------------------------------------------
# DESIGN PALETTE
# --------------------------------------------------------------------------
C_DARK_BLUE = "#1162AC"
C_MED_BLUE = "#1F89D8"
C_PINK = "#F15CE3"
C_YELLOW = "#DAFF15"
C_LIME = "#BDD409"
C_BLACK = "#000000"
C_GREY = "#e6e6e6"
FONT_MAIN = "Montserrat, Arial Black, sans-serif"


# --------------------------------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------------------------------
def _normalize(val, min_v, max_v):
    if val is None:
        return 50
    return max(0, min(100, (val - min_v) / (max_v - min_v) * 100))


def _calculate_sub_score(val, min_need, max_need, penalty_factor=5):
    """Calculates match score (0-100) for a specific parameter."""
    if val is None:
        return 0
    if min_need <= val <= max_need:
        return 100
    if val < min_need:
        diff = min_need - val
        return max(0, 100 - (diff * penalty_factor))
    if val > max_need:
        diff = val - max_need
        return max(0, 100 - (diff * penalty_factor))
    return 0


def _convert_real_data_to_df(real_data):
    """Prepares data for the Radar Chart"""
    climate = real_data["climate"]
    plant = real_data["plant"]

    bounds = {
        "Temperature": (-10, 40),
        "Precipitation": (0, 2000),
        "pH": (4, 9),
        "Sunlight": (0, 100),
        "Soil Moisture": (0, 100),
    }

    # Normalize values relative to global bounds
    p_temp = _normalize(
        (plant["Min_Temp"] + plant["Max_Temp"]) / 2, *bounds["Temperature"]
    )
    p_rain = _normalize(
        (plant["Min_Rain"] + plant["Max_Rain"]) / 2, *bounds["Precipitation"]
    )
    p_ph = _normalize((plant["Min_pH"] + plant["Max_pH"]) / 2, *bounds["pH"])

    l_temp = _normalize(climate["mean_temp"], *bounds["Temperature"])
    l_rain = _normalize(climate["rain"], *bounds["Precipitation"])
    l_ph = _normalize(climate.get("ph", 6.5), *bounds["pH"])
    l_sun = _normalize(climate.get("sun", 80), *bounds["Sunlight"])
    l_hum = _normalize(climate.get("humidity", 60), *bounds["Soil Moisture"])

    data = [
        ("Temp", p_temp, l_temp),  # Changed Temperature to Temp
        ("Rainfall", p_rain, l_rain),
        ("Sunlight", 80, l_sun),
        ("Soil Moisture", 60, l_hum),
        ("pH", p_ph, l_ph),
    ]

    df = pd.DataFrame(data, columns=["condition", "plant_optimum", "local_value"])
    df["difference"] = df["local_value"] - df["plant_optimum"]
    return df


# --------------------------------------------------------------------------
# CHART GENERATORS
# --------------------------------------------------------------------------


def create_circular_gauge(score, real_data=None, height=350):
    """
    Modern Segmented Block Gauge showing REAL DATA METRICS at the top.
    """
    fig = go.Figure()

    # --- 1. DETERMINE COLOR ---
    if score >= 80:
        active_color = "#2ECC71"  # Green
    elif score >= 50:
        active_color = C_YELLOW
    else:
        active_color = "#E74C3C"  # Red

    # --- 2. BUILD SEGMENTS (Visuals) ---
    total_segments = 40
    lit_segments = int(score / (100 / total_segments))
    colors = [active_color] * lit_segments + [C_GREY] * (total_segments - lit_segments)

    fig.add_trace(
        go.Pie(
            values=[1] * total_segments,
            hole=0.85,
            sort=False,
            direction="clockwise",
            textinfo="none",
            marker=dict(colors=colors, line=dict(color="white", width=3)),
            domain={"x": [0, 1], "y": [0, 0.85]},
            hoverinfo="skip",
        )
    )

    # --- 3. CENTER TEXT (Score) ---
    fig.add_annotation(
        x=0.5,
        y=0.425,
        text=f"{int(score)}",
        showarrow=False,
        font=dict(size=70, family=FONT_MAIN, color=C_DARK_BLUE),
    )

    # 4. Suitability Label
    fig.add_annotation(
        x=0.5,
        y=0.20,  # Slightly below number
        text="SUITABILITY",
        showarrow=False,
        font=dict(size=14, family="Poppins", color="gray", weight="bold"),
    )

    # 5. Top Metrics (Temp, Rain, pH)
    if real_data:
        clim = real_data["climate"]

        val_temp = f"{clim['min_temp']}°"
        val_rain = f"{clim['rain']}mm"
        val_ph = f"{clim['ph']}"

        metrics = [
            (val_temp, "MIN TEMP", 0.15),
            (val_rain, "RAIN", 0.5),
            (val_ph, "pH", 0.85),
        ]

        for val, label, x_pos in metrics:
            # Value
            fig.add_annotation(
                x=x_pos,
                y=1.0,  # Top edge
                text=str(val),
                showarrow=False,
                font=dict(size=22, family=FONT_MAIN, color=C_BLACK),
            )
            # Label
            fig.add_annotation(
                x=x_pos,
                y=0.90,  # Just below value
                text=label,
                showarrow=False,
                font=dict(size=11, family="Poppins", color="gray"),
            )

    fig.update_layout(
        height=height,
        margin=dict(l=10, r=25, t=30, b=25),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return fig


def create_radar_chart(plant_name, loc_name, real_data, height=350):
    if not real_data:
        return go.Figure()

    df = _convert_real_data_to_df(real_data)

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=df["plant_optimum"].tolist() + [df["plant_optimum"].iloc[0]],
            theta=df["condition"].tolist() + [df["condition"].iloc[0]],
            fill="toself",
            name=f"{plant_name}",  # Changed to Plant Name
            line=dict(color=C_BLACK, width=1),
            fillcolor="rgba(241, 92, 227, 0.3)",
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=df["local_value"].tolist() + [df["local_value"].iloc[0]],
            theta=df["condition"].tolist() + [df["condition"].iloc[0]],
            fill="toself",
            name="Location",  # Changed to Location
            line=dict(color=C_BLACK, width=3),
            fillcolor="rgba(31, 137, 216, 0.3)",
        )
    )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=8)),
            angularaxis=dict(tickfont=dict(size=10)),  # Smaller font for labels
        ),
        showlegend=True,
        legend=dict(
            orientation="h", y=-0.15, font=dict(size=10)
        ),  # Moved legend down, smaller text
        height=height,
        margin=dict(t=10, b=30, l=35, r=35),  # Reverted margins to be balanced
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Poppins"},
    )
    return fig


def create_diverging_bar_chart(plant_name, loc_name, real_data, height=350):
    if not real_data:
        return go.Figure()
    df = _convert_real_data_to_df(real_data)

    colors = [C_PINK if x < 0 else C_LIME for x in df["difference"]]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=df["condition"],
            x=df["difference"],
            orientation="h",
            marker=dict(color=colors, line=dict(color=C_BLACK, width=1)),
        )
    )
    fig.update_layout(
        height=height,
        margin=dict(
            t=20, b=20, l=10, r=40
        ),  # Increased right margin to prevent overflow
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Poppins"},
        xaxis=dict(zeroline=True, showgrid=False),
        yaxis=dict(tickfont=dict(size=11)),
    )
    return fig


def create_top_countries_chart(top_countries_df, height=500):
    if top_countries_df.empty:
        return go.Figure()

    df = top_countries_df.sort_values("avg_score", ascending=True)
    colors = [
        "#2ECC71" if s >= 70 else (C_YELLOW if s >= 40 else "#E74C3C")
        for s in df["avg_score"]
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=df["country"],
            x=df["avg_score"],
            orientation="h",
            marker=dict(color=colors, line=dict(color=C_BLACK, width=1.5)),
            text=[f"{x:.0f}" for x in df["avg_score"]],
            textposition="outside",
        )
    )
    fig.update_layout(
        height=height,
        margin=dict(
            l=10, r=80, t=10, b=10
        ),  # Increased right margin to prevent label overflow
        xaxis=dict(showgrid=False, range=[0, 115], showticklabels=False),
        yaxis=dict(title=""),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Poppins"},
    )
    return fig
