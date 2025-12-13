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
FONT_MAIN = "Montserrat, Arial Black, sans-serif"


# --------------------------------------------------------------------------
# HELPER
# --------------------------------------------------------------------------
def _normalize(val, min_v, max_v):
    if val is None:
        return 50
    return max(0, min(100, (val - min_v) / (max_v - min_v) * 100))


def _calculate_sub_score(val, min_need, max_need, penalty_factor=5):
    """
    Calculates a simple 0-100 match score for a specific parameter.
    penalty_factor: Points deducted per unit of deviation.
    """
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
    climate = real_data["climate"]
    plant = real_data["plant"]

    bounds = {
        "Temperature": (-10, 40),
        "Precipitation": (0, 2000),
        "pH": (4, 9),
        "Sunlight": (0, 100),
        "Soil Moisture": (0, 100),
    }

    # Normalize for Radar Chart
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
        ("Temperature", p_temp, l_temp),
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
    # 1. Determine Color
    if score >= 80:
        color = "#2ECC71"
    elif score >= 50:
        color = C_YELLOW
    else:
        color = "#E74C3C"

    fig = go.Figure()

    # 2. Main Gauge
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={
                "suffix": "%",
                "font": {"size": 60, "family": FONT_MAIN, "color": C_DARK_BLUE},
            },
            title={
                "text": "OVERALL SUITABILITY",
                "font": {"size": 14, "family": "Poppins", "color": "gray"},
                "align": "center",
            },
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 0, "visible": False},
                "bar": {"color": color, "thickness": 0.85},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 0,
                "steps": [{"range": [0, 100], "color": "#f0f2f6"}],
            },
            domain={"x": [0, 1], "y": [0, 0.75]},
        )
    )

    # 3. Add Top Metrics (Temp, Rain, pH)
    if real_data:
        clim = real_data["climate"]
        plant = real_data["plant"]

        # --- FIXED TEMP LOGIC ---
        # Don't use Mean Temp. Check Extremes instead.

        # 1. Cold Check (Strict penalty for freezing)
        if clim["min_temp"] < plant["Min_Temp"]:
            diff = plant["Min_Temp"] - clim["min_temp"]
            s_temp_min = max(0, 100 - (diff * 10))
        else:
            s_temp_min = 100

        # 2. Heat Check
        if clim["max_temp"] > plant["Max_Temp"]:
            diff = clim["max_temp"] - plant["Max_Temp"]
            s_temp_max = max(0, 100 - (diff * 5))
        else:
            s_temp_max = 100

        # The Temp score is the worst of the two (Weakest Link)
        s_temp = min(s_temp_min, s_temp_max)

        # --- RAIN LOGIC ---
        # Adjusted penalty factor to 0.05 (More forgiving)
        # 200mm difference = -10% score
        s_rain = _calculate_sub_score(
            clim["rain"], plant["Min_Rain"], plant["Max_Rain"], penalty_factor=0.05
        )

        # --- pH LOGIC ---
        # Strict: 30 pts per unit
        s_ph = _calculate_sub_score(
            clim["ph"], plant["Min_pH"], plant["Max_pH"], penalty_factor=30
        )

        # Temp Indicator
        fig.add_trace(
            go.Indicator(
                mode="number",
                value=s_temp,
                number={"suffix": "%", "font": {"size": 24, "color": C_BLACK}},
                title={"text": "TEMP", "font": {"size": 12, "color": "gray"}},
                domain={"x": [0.1, 0.3], "y": [0.8, 1]},
            )
        )
        # Rain Indicator
        fig.add_trace(
            go.Indicator(
                mode="number",
                value=s_rain,
                number={"suffix": "%", "font": {"size": 24, "color": C_BLACK}},
                title={"text": "RAIN", "font": {"size": 12, "color": "gray"}},
                domain={"x": [0.4, 0.6], "y": [0.8, 1]},
            )
        )
        # pH Indicator
        fig.add_trace(
            go.Indicator(
                mode="number",
                value=s_ph,
                number={"suffix": "%", "font": {"size": 24, "color": C_BLACK}},
                title={"text": "pH", "font": {"size": 12, "color": "gray"}},
                domain={"x": [0.7, 0.9], "y": [0.8, 1]},
            )
        )

    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=30, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Poppins"},
    )
    return fig


def create_radar_chart(plant_name, loc_name, real_data, height=350):
    if not real_data:
        return go.Figure()

    df = _convert_real_data_to_df(real_data)

    fig = go.Figure()
    # Ideal
    fig.add_trace(
        go.Scatterpolar(
            r=df["plant_optimum"].tolist() + [df["plant_optimum"].iloc[0]],
            theta=df["condition"].tolist() + [df["condition"].iloc[0]],
            fill="toself",
            name="Target",
            line=dict(color=C_BLACK, width=1),
            fillcolor="rgba(241, 92, 227, 0.3)",
        )
    )
    # Actual
    fig.add_trace(
        go.Scatterpolar(
            r=df["local_value"].tolist() + [df["local_value"].iloc[0]],
            theta=df["condition"].tolist() + [df["condition"].iloc[0]],
            fill="toself",
            name="Actual",
            line=dict(color=C_BLACK, width=3),
            fillcolor="rgba(31, 137, 216, 0.3)",
        )
    )

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True,
        legend=dict(orientation="h", y=-0.1),
        height=height,
        margin=dict(t=20, b=20),
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
        margin=dict(t=20, b=20, l=10, r=10),
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
        margin=dict(l=10, r=30, t=10, b=10),
        xaxis=dict(showgrid=False, range=[0, 115], showticklabels=False),
        yaxis=dict(title=""),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Poppins"},
    )
    return fig
