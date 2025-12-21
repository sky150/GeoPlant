import plotly.graph_objects as go
import pandas as pd
import numpy as np

# --------------------------------------------------------------------------
# DESIGN PALETTE
# --------------------------------------------------------------------------
C_DARK_BLUE = "#1F89D8"
C_MED_BLUE = "#1F89D8"
C_PINK = "#F15CE3"
C_YELLOW = "#DAFF15"
C_LIME = "#BDD409"
C_BLACK = "#000000"
C_GREY = "#e6e6e6"
FONT_MAIN = "Montserrat, Arial Black, sans-serif"

TITLE_CONFIG = dict(
    x=0.5,
    xanchor="right",
    y=0.99,
    font=dict(family="Montserrat", size=16, color="#333", weight=900),
)


# --------------------------------------------------------------------------
# LOGIC: CONVERT REAL DATA TO RELATIVE PERCENTAGES
# --------------------------------------------------------------------------
def _normalize(val, min_v, max_v):
    if val is None:
        return 50
    return max(0, min(100, (val - min_v) / (max_v - min_v) * 100))


def _convert_real_data_to_df(real_data):
    climate = real_data["climate"]
    plant = real_data["plant"]
    water_source = real_data.get("water_source", "Rainfed Only")

    # 1. Ideals
    p_temp_opt = (plant["Min_Temp"] + plant["Max_Temp"]) / 2
    p_rain_opt = (plant["Min_Rain"] + plant["Max_Rain"]) / 2
    p_ph_opt = (plant["Min_pH"] + plant["Max_pH"]) / 2
    p_sun_opt = plant.get("Sun_Need", 80)
    p_hum_opt = plant.get("Ideal_Hum", 50)

    # 2. Local Data
    l_temp = climate["mean_temp"]

    # IRRIGATION LOGIC: If Irrigated, pretend rain is optimal
    if water_source == "Irrigated":
        l_rain = p_rain_opt
    else:
        l_rain = climate["rain"]

    l_ph = climate.get("ph", 6.5)
    l_sun = climate.get("sun", 80)
    l_hum = climate.get("humidity", 60)

    # 3. Ratio Calculation
    def calculate_ratio(local, optimum, is_interval=False):
        if optimum == 0:
            return 100 + (local * 10)
        ratio = (local / optimum) * 100
        return ratio

    # 4. Compile
    data = [
        ("Temp", 100, calculate_ratio(l_temp, p_temp_opt, is_interval=True)),
        ("Rain", 100, calculate_ratio(l_rain, p_rain_opt)),
        ("Sun", 100, calculate_ratio(l_sun, p_sun_opt)),
        ("Hum", 100, calculate_ratio(l_hum, p_hum_opt)),
        ("pH", 100, calculate_ratio(l_ph, p_ph_opt, is_interval=True)),
    ]

    df = pd.DataFrame(data, columns=["condition", "plant_optimum", "local_value"])
    df["difference"] = df["local_value"] - 100

    # Mark Rain as "Artificial" if irrigated for coloring later
    df["is_artificial"] = False
    if water_source == "Irrigated":
        df.loc[df["condition"] == "Rain", "is_artificial"] = True

    return df


# --------------------------------------------------------------------------
# CHART GENERATORS
# --------------------------------------------------------------------------


def create_circular_gauge(score, real_data=None, height=350):
    """
    Modern Segmented Block Gauge showing REAL DATA METRICS at the top.
    """
    fig = go.Figure()

    # Get bonus
    bonus = real_data.get("bonus", 0) if real_data else 0
    base_score = score - bonus

    # 1. Color Logic
    if score >= 80:
        active_color = C_LIME
    elif score >= 50:
        active_color = C_YELLOW
    else:
        active_color = C_PINK

    # 2. Segments
    total_segments = 40
    # Segments for the "Natural" score
    base_lit = int(base_score / (100 / total_segments))
    # Segments for the "Bonus" (Irrigation)
    bonus_lit = int(bonus / (100 / total_segments))

    # Construct color array: [Base Color] + [Blue Bonus] + [Grey]
    colors = (
        [active_color] * base_lit
        + [C_MED_BLUE] * bonus_lit
        + [C_GREY] * (total_segments - base_lit - bonus_lit)
    )

    fig.add_trace(
        go.Pie(
            values=[1] * total_segments,
            hole=0.85,
            sort=False,
            direction="clockwise",
            textinfo="none",
            marker=dict(colors=colors, line=dict(color="white", width=3)),
            domain={"x": [0, 1], "y": [0, 1]},
            hoverinfo="skip",
        )
    )

    # --- 3. CENTER TEXT (Score) ---
    fig.add_annotation(
        x=0.5,
        y=0.55,
        text=f"{int(score)}",
        showarrow=False,
        font=dict(size=70, family=FONT_MAIN, color=C_DARK_BLUE),
    )

    # 4. Suitability Label
    fig.add_annotation(
        x=0.5,
        y=0.30,
        text="SUITABILITY",
        showarrow=False,
        font=dict(size=14, family="Poppins", color="gray", weight="bold"),
    )

    fig.update_layout(
        title={**TITLE_CONFIG, "text": "<b>SUITABILITY SCORE</b>"},
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

    # Dynamische Skalierung: Wenn ein Wert 150% ist, muss der Chart bis mind. 150 gehen
    max_val = df["local_value"].max()
    chart_range = [0, max(140, max_val + 10)]  # Mindestens bis 140, sonst dynamisch

    fig = go.Figure()

    # 1. Die Pflanze (Referenz = 100%)
    fig.add_trace(
        go.Scatterpolar(
            r=df["plant_optimum"].tolist() + [df["plant_optimum"].iloc[0]],
            theta=df["condition"].tolist() + [df["condition"].iloc[0]],
            fill="toself",
            name=f"{plant_name} (Optimum)",
            line=dict(color=C_BLACK, width=2, dash="dot"),
            fillcolor="rgba(200, 200, 200, 0.2)",  # Dezentes Grau für Basis
            hoverinfo="skip",
        )
    )

    # 2. Der Ort (Variabel)
    fig.add_trace(
        go.Scatterpolar(
            r=df["local_value"].tolist() + [df["local_value"].iloc[0]],
            theta=df["condition"].tolist() + [df["condition"].iloc[0]],
            fill="toself",
            name="Location Data",
            line=dict(color=C_PINK, width=3),
            fillcolor="rgba(241, 92, 227, 0.4)",
        )
    )

    fig.update_layout(
        title=dict(
            text="<b>CONDITIONS</b>",
            x=0.32,
            xanchor="right",
            y=0.99,
            font=dict(family="Montserrat", size=16, color="#333"),
        ),
        polar=dict(
            radialaxis=dict(visible=True, range=chart_range, tickfont=dict(size=8)),
            angularaxis=dict(tickfont=dict(size=10)),
        ),
        showlegend=True,
        legend=dict(orientation="h", y=-0.15, font=dict(size=10)),
        height=height,
        margin=dict(t=30, b=10, l=35, r=35),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Poppins"},
    )
    return fig


def create_diverging_bar_chart(plant_name, loc_name, real_data, height=350):
    if not real_data:
        return go.Figure()

    df = _convert_real_data_to_df(real_data)

    # WICHTIG: Sortierung nach fester Reihenfolge erzwingen
    order = ["Temp", "Hum", "Rain", "Sun", "pH"]
    df["condition"] = pd.Categorical(df["condition"], categories=order, ordered=True)
    df = df.sort_values("condition", ascending=False)  # Reversed für horizontale Bars

    colors = [C_MED_BLUE if x < 0 else C_PINK for x in df["difference"]]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=df["condition"],
            x=df["difference"],
            orientation="h",
            marker=dict(color=colors, line=dict(color=C_BLACK, width=1)),
            text=[f"{x:+.0f}%" for x in df["difference"]],
            textposition="outside",
        )
    )

    max_diff = max(abs(df["difference"].min()), abs(df["difference"].max()))
    limit = max(50, max_diff + 20)

    fig.update_layout(
        title=dict(
            text="<b>DEVIATION</b>",
            x=0.3,
            xanchor="right",
            y=0.99,
            font=dict(family="Montserrat", size=16, color="#333"),
        ),
        height=height,
        margin=dict(t=30, b=20, l=10, r=40),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Poppins"},
        xaxis=dict(
            zeroline=True,
            showgrid=True,
            range=[-limit, limit],
        ),
        yaxis=dict(
            tickfont=dict(size=11), categoryorder="array", categoryarray=order[::-1]
        ),
    )
    return fig


def create_top_countries_chart(top_countries_df, height=500):
    """
    Zeigt Top Countries als % vom Maximum (100% = bester Ort).
    """
    if top_countries_df.empty:
        return go.Figure()

    df = top_countries_df.sort_values("avg_score", ascending=True).copy()

    # Konvertiere zu Prozent vom Maximum
    max_score = df["avg_score"].max()
    if max_score > 0:
        df["percentage"] = (df["avg_score"] / max_score) * 100
    else:
        df["percentage"] = 0

    # --- FARBLOGIK ---
    # Wir weisen jedem Score direkt die Design-Farbe zu
    colors = []
    for s in df["avg_score"]:
        if s >= 75:
            colors.append(C_LIME)  # Top: Lime Green
        elif s >= 45:
            colors.append(C_MED_BLUE)  # Mittel: Medium Blue
        else:
            colors.append(C_PINK)  # Schlecht: Pink

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=df["country"],
            x=df["avg_score"],
            orientation="h",
            # Dickere schwarze Linie (width=2) für den Comic-Look
            marker=dict(color=colors, line=dict(color=C_BLACK, width=2)),
            text=[f"{x:.0f}%" for x in df["avg_score"]],
            # textposition="outside",
            textfont=dict(family=FONT_MAIN, size=12, color=C_BLACK),
        )
    )
    fig.update_layout(
        title=dict(
            text="<b>TOP REGIONS</b>",
            x=0.45,
            xanchor="right",
            y=0.99,
            font=dict(family="Montserrat", size=16, color="#333"),
        ),
        height=height,
        margin=dict(r=15, t=30, b=10),
        xaxis=dict(showgrid=False, range=[0, 115], showticklabels=False),
        yaxis=dict(title="", tickfont=dict(family="Poppins", size=11, color="black")),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Poppins"},
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig
