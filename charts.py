import plotly.graph_objects as go
import pandas as pd
import numpy as np

# Fallback Data
from charts_example_data import (
    get_plant_location_profile,
    compute_location_scores_for_plant,
    plants as mock_plants
)

# --------------------------------------------------------------------------
# DESIGN PALETTE (MATCHING STYLE.CSS)
# --------------------------------------------------------------------------
C_DARK_BLUE = "#1162AC"
C_MED_BLUE = "#1F89D8"
C_PINK = "#F15CE3"
C_YELLOW = "#DAFF15"
C_LIME = "#BDD409"
C_BLACK = "#000000"

# Font Settings
FONT_MAIN = "Montserrat, Arial Black, sans-serif"

# --------------------------------------------------------------------------
# HELPER
# --------------------------------------------------------------------------
def _normalize(val, min_v, max_v):
    if val is None: return 50
    return max(0, min(100, (val - min_v) / (max_v - min_v) * 100))

def _convert_real_data_to_df(real_data):
    climate = real_data['climate']
    plant = real_data['plant']

    bounds = {
        "Temperature": (-10, 40), "Precipitation": (0, 2000),
        "pH": (4, 9), "Sunlight": (0, 100), "Soil Moisture": (0, 100)
    }

    plant_temp_avg = (plant['Min_Temp'] + plant['Max_Temp']) / 2
    opt_temp = _normalize(plant_temp_avg, *bounds["Temperature"])
    plant_rain_avg = (plant['Min_Rain'] + plant['Max_Rain']) / 2
    opt_rain = _normalize(plant_rain_avg, *bounds["Precipitation"])
    plant_ph_avg = (plant['Min_pH'] + plant['Max_pH']) / 2
    opt_ph = _normalize(plant_ph_avg, *bounds["pH"])

    opt_sun = 80; opt_moist = 60

    loc_temp = _normalize(climate['mean_temp'], *bounds["Temperature"])
    loc_rain = _normalize(climate['rain'], *bounds["Precipitation"])
    loc_ph = _normalize(climate.get('ph', 6.5), *bounds["pH"])
    loc_sun = _normalize(climate.get('sun', 50), *bounds["Sunlight"])
    loc_moist = _normalize(climate.get('humidity', 50), *bounds["Soil Moisture"])

    data = [
        ("Temperature", opt_temp, loc_temp),
        ("Precipitation", opt_rain, loc_rain),
        ("Sunlight", opt_sun, loc_sun),
        ("Soil Moisture", opt_moist, loc_moist),
        ("pH", opt_ph, loc_ph)
    ]

    df = pd.DataFrame(data, columns=["condition", "plant_optimum", "local_value"])
    df["difference"] = df["local_value"] - df["plant_optimum"]
    return df

# --------------------------------------------------------------------------
# CHART GENERATORS (Added 'height' parameter)
# --------------------------------------------------------------------------

def create_radar_chart(plant_name: str, location_name: str, real_data=None, height=500):
    use_fallback = False
    df = None

    if real_data:
        try:
            df = _convert_real_data_to_df(real_data)
            chart_title = f"LIVE DATA: {plant_name.upper()}"
        except: use_fallback = True
    else: use_fallback = True

    if use_fallback:
        if plant_name not in mock_plants: plant_name = "Tomato"
        df = get_plant_location_profile(plant_name, location_name)
        chart_title = f"SIMULATION: {plant_name.upper()}"

    fig = go.Figure()

    # TRACE 1: PLANT (IDEAL)
    fig.add_trace(go.Scatterpolar(
        r=df["plant_optimum"].tolist() + [df["plant_optimum"].iloc[0]],
        theta=df["condition"].tolist() + [df["condition"].iloc[0]],
        fill='toself', name=f'{plant_name} (Target)',
        line=dict(color=C_BLACK, width=3),
        fillcolor='rgba(241, 92, 227, 0.4)',
        marker=dict(symbol="circle", size=8, color=C_PINK, line=dict(color=C_BLACK, width=1))
    ))

    # TRACE 2: LOCATION (ACTUAL)
    fig.add_trace(go.Scatterpolar(
        r=df["local_value"].tolist() + [df["local_value"].iloc[0]],
        theta=df["condition"].tolist() + [df["condition"].iloc[0]],
        fill='toself', name=f'Location',
        line=dict(color=C_BLACK, width=3, dash='dot'),
        fillcolor='rgba(31, 137, 216, 0.4)',
        marker=dict(symbol="square", size=8, color=C_MED_BLUE, line=dict(color=C_BLACK, width=1))
    ))

    # Dynamic Margins
    m_t = 80 if height > 400 else 30
    m_b = 40 if height > 400 else 20

    fig.update_layout(
        font=dict(family=FONT_MAIN, size=14, color="black"),
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], color="black", showline=False, gridcolor="gray"),
            angularaxis=dict(color="black", gridcolor="#ddd", linecolor="black", linewidth=2),
            bgcolor="white"
        ),
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5,
            bordercolor=C_BLACK, borderwidth=2, bgcolor=C_YELLOW
        ),
        margin=dict(t=m_t, b=m_b),
        height=height, # DYNAMIC HEIGHT
        paper_bgcolor='rgba(255,255,255, 0.95)',
        plot_bgcolor='rgba(255,255,255, 0.95)'
    )
    return fig


def create_diverging_bar_chart(plant_name: str, location_name: str, real_data=None, height=400):
    use_fallback = False
    df = None

    if real_data:
        try: df = _convert_real_data_to_df(real_data)
        except: use_fallback = True
    else: use_fallback = True

    if use_fallback:
        if plant_name not in mock_plants: plant_name = "Tomato"
        df = get_plant_location_profile(plant_name, location_name)

    colors = [C_PINK if x < 0 else C_LIME for x in df["difference"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df["condition"], x=df["difference"],
        orientation='h',
        marker=dict(
            color=colors,
            line=dict(color=C_BLACK, width=2)
        ),
        text=[f"{val:+.0f}" for val in df["difference"]],
        textposition='outside',
        textfont=dict(family=FONT_MAIN, size=14, color="black", weight="bold")
    ))

    # Titel ausblenden bei kleinen Dashboard-Charts für mehr Platz
    title_text = f"DEVIATION FROM TARGET" if height > 350 else ""
    m_t = 50 if height > 350 else 20

    fig.update_layout(
        font=dict(family=FONT_MAIN, color="black"),
        title=dict(text=title_text, x=0.5, xanchor='center'),
        xaxis=dict(
            title="Difference",
            zeroline=True, zerolinecolor=C_BLACK, zerolinewidth=3,
            showgrid=True, gridcolor="#eee"
        ),
        yaxis=dict(showgrid=False),
        height=height, # DYNAMIC HEIGHT
        margin=dict(t=m_t, b=20, l=10, r=10),
        showlegend=False,
        paper_bgcolor='rgba(255,255,255, 0.95)',
        plot_bgcolor='rgba(255,255,255, 0.95)'
    )
    return fig


def create_bubble_map(plant_name: str, height=500):
    if plant_name not in mock_plants: plant_name_for_map = "Tomato"
    else: plant_name_for_map = plant_name

    scores = compute_location_scores_for_plant(plant_name_for_map)

    fig = go.Figure()
    fig.add_trace(go.Scattergeo(
        lon=scores["lon"], lat=scores["lat"],
        text=scores["location"], mode='markers',
        marker=dict(
            size=scores["growth_score"] * 0.6,
            color=scores["growth_score"],
            colorscale=[[0, C_PINK], [0.5, C_YELLOW], [1, C_LIME]],
            showscale=False,
            line=dict(color=C_BLACK, width=1)
        )
    ))

    m_t = 60 if height > 350 else 10

    fig.update_layout(
        title=dict(text=f"GLOBAL MATCHES (SIMULATION)", x=0.5, xanchor='center', font=dict(family=FONT_MAIN)),
        geo=dict(
            projection_type='natural earth',
            showland=True, landcolor='#f0f2f6',
            showcountries=True, countrycolor=C_BLACK,
            showocean=True, oceancolor=C_MED_BLUE
        ),
        height=height, # DYNAMIC HEIGHT
        margin=dict(l=0, r=0, t=m_t, b=0),
        paper_bgcolor='rgba(255,255,255, 0.95)'
    )
    return fig
