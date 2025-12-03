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
# HELPER: Real Data to Chart Data Converter
# --------------------------------------------------------------------------
def _normalize(val, min_v, max_v):
    """Hilfsfunktion um absolute Werte (z.B. 20°C) auf 0-100 Skala zu bringen"""
    if val is None: return 50
    # Clipping, damit wir nicht aus dem Chart fallen
    return max(0, min(100, (val - min_v) / (max_v - min_v) * 100))

def _convert_real_data_to_df(real_data):
    """
    Wandelt das Dictionary aus backend_api.py in ein DataFrame um,
    das exakt so aussieht wie das aus charts_example_data.py.
    """
    climate = real_data['climate']
    plant = real_data['plant']

    # Globale Grenzen für die Normalisierung (Damit Charts vergleichbar sind)
    # Temp: -10 bis 40°C, Rain: 0 bis 2000mm, pH: 4 bis 9
    bounds = {
        "Temperature": (-10, 40),
        "Precipitation": (0, 2000),
        "pH": (4, 9),
        "Sunlight": (0, 100),       # Prozent
        "Soil Moisture": (0, 100)   # Prozent (als Proxy für Humidity/Seasonality)
    }

    # 1. Berechne "Plant Optimum" (Mittelwert aus Min/Max Bedarf)
    # Wir mappen die echten DB-Werte auf die Chart-Kategorien

    # Temp
    plant_temp_avg = (plant['Min_Temp'] + plant['Max_Temp']) / 2
    opt_temp = _normalize(plant_temp_avg, *bounds["Temperature"])

    # Rain
    plant_rain_avg = (plant['Min_Rain'] + plant['Max_Rain']) / 2
    opt_rain = _normalize(plant_rain_avg, *bounds["Precipitation"])

    # pH
    plant_ph_avg = (plant['Min_pH'] + plant['Max_pH']) / 2
    opt_ph = _normalize(plant_ph_avg, *bounds["pH"])

    # Mocked/Simulated Plant needs for others
    opt_sun = 80
    opt_moist = 60

    # 2. Berechne "Local Value" (Echte Messwerte)
    loc_temp = _normalize(climate['mean_temp'], *bounds["Temperature"])
    loc_rain = _normalize(climate['rain'], *bounds["Precipitation"])
    loc_ph = _normalize(climate.get('ph', 6.5), *bounds["pH"])
    loc_sun = _normalize(climate.get('sun', 50), *bounds["Sunlight"])

    # Nutze 'seasonality' oder 'humidity' als Proxy für Moisture
    loc_moist = _normalize(climate.get('humidity', 50), *bounds["Soil Moisture"])

    # 3. DataFrame bauen
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
# CHART GENERATORS
# --------------------------------------------------------------------------

def create_radar_chart(plant_name: str, location_name: str, real_data=None):
    """
    Erstellt Radar-Chart.
    Logik: Versucht zuerst 'real_data' zu nutzen. Falls Fehler -> Fallback auf Mock Data.
    """
    use_fallback = False
    df = None

    # 1. Versuche echte Daten zu nutzen
    if real_data:
        try:
            df = _convert_real_data_to_df(real_data)
            chart_title = f"Wachstumsbedingungen (Live Data): {plant_name}"
            col_ideal = '#10b981'
            col_act = '#3b82f6'
        except Exception as e:
            print(f"Chart Error (Real Data): {e}")
            use_fallback = True
    else:
        use_fallback = True

    # 2. Fallback Logic
    if use_fallback:
        # Prüfen ob Pflanze in Mock Data existiert, sonst Default
        if plant_name not in mock_plants:
            plant_name = "Tomato" # Ultimate Fallback
            location_name = "Valencia"

        df = get_plant_location_profile(plant_name, location_name)
        chart_title = f"Wachstumsbedingungen (Beispiel): {plant_name}"

    # 3. Plotting (Identisch für beide Datenquellen)
    fig = go.Figure()

    # Pflanze (Ideal)
    fig.add_trace(go.Scatterpolar(
        r=df["plant_optimum"].tolist() + [df["plant_optimum"].iloc[0]],
        theta=df["condition"].tolist() + [df["condition"].iloc[0]],
        fill='toself', name=f'{plant_name} (Ideal)',
        line=dict(color='#10b981', width=2),
        fillcolor='rgba(16, 185, 129, 0.3)'
    ))

    # Standort (Aktuell)
    fig.add_trace(go.Scatterpolar(
        r=df["local_value"].tolist() + [df["local_value"].iloc[0]],
        theta=df["condition"].tolist() + [df["condition"].iloc[0]],
        fill='toself', name=f'Standort (Aktuell)',
        line=dict(color='#3b82f6', width=2),
        fillcolor='rgba(59, 130, 246, 0.3)'
    ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True,
        title=dict(text=chart_title, x=0.5, xanchor='center'),
        height=500
    )
    return fig


def create_diverging_bar_chart(plant_name: str, location_name: str, real_data=None):
    """
    Erstellt Bar-Chart.
    Logik: Versucht zuerst 'real_data' zu nutzen. Falls Fehler -> Fallback auf Mock Data.
    """
    use_fallback = False
    df = None

    if real_data:
        try:
            df = _convert_real_data_to_df(real_data)
        except:
            use_fallback = True
    else:
        use_fallback = True

    if use_fallback:
        if plant_name not in mock_plants: plant_name = "Tomato"
        df = get_plant_location_profile(plant_name, location_name)

    # Farben basierend auf Abweichung
    colors = ['#ef4444' if x < 0 else '#10b981' for x in df["difference"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df["condition"], x=df["difference"],
        orientation='h',
        marker=dict(color=colors, line=dict(color='rgba(0,0,0,0.3)', width=1)),
        text=[f"{val:+.0f}" for val in df["difference"]],
        textposition='outside'
    ))

    fig.update_layout(
        title=dict(text=f"Abweichung vom Ideal: {plant_name}", x=0.5, xanchor='center'),
        xaxis=dict(title="Abweichung (Negativ = Mangel / Positiv = Überschuss)"),
        height=400,
        showlegend=False
    )
    return fig


def create_bubble_map(plant_name: str):
    """
    Erstellt Bubble Map.
    ACHTUNG: Da das Backend aktuell nur EINEN Punkt berechnet und keine
    weltweite Heatmap liefert, nutzen wir hier IMMER die Mock-Daten
    für den 'Globalen Kontext'.
    """
    # Fallback auf Mock, wenn Pflanze unbekannt
    if plant_name not in mock_plants:
        plant_name_for_map = "Tomato"
    else:
        plant_name_for_map = plant_name

    scores = compute_location_scores_for_plant(plant_name_for_map)

    fig = go.Figure()
    fig.add_trace(go.Scattergeo(
        lon=scores["lon"], lat=scores["lat"],
        text=scores["location"], mode='markers',
        marker=dict(
            size=scores["growth_score"] * 0.5,
            color=scores["growth_score"],
            colorscale='Viridis',
            showscale=True
        )
    ))

    fig.update_layout(
        title=dict(text=f"Globale Alternativen (Simulation für {plant_name_for_map})", x=0.5, xanchor='center'),
        geo=dict(projection_type='natural earth', showland=True, showcountries=True),
        height=500, margin=dict(l=0, r=0, t=60, b=0)
    )
    return fig
