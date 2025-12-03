import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium

# Imports
import backend_api
# Importiere Charts und die Fallback Daten (nur für die Dropdown-Auswahl falls DB leer)
from charts import create_radar_chart, create_diverging_bar_chart, create_bubble_map
import charts_example_data

# ---------------------------------------------------------
# UI CONFIGURATION & CSS
# ---------------------------------------------------------
st.set_page_config(page_title="GeoPlant Analytics", layout="wide", page_icon="🌱")

st.markdown("""
<style>
    .story-step {
        min-height: 90vh;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        padding: 2rem;
        border-bottom: 1px solid #f0f2f6;
    }
    .story-title {
        font-size: 2.8rem !important;
        font-weight: 700 !important;
        color: #1e293b;
        text-align: center;
    }
    .story-text {
        font-size: 1.3rem !important;
        color: #64748b;
        text-align: center;
        max-width: 800px;
        margin: 0 auto 3rem auto;
    }
    .dashboard-container {
        background-color: #f8fafc;
        padding: 3rem;
        border-radius: 20px;
        margin-top: 5rem;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------
if 'lat' not in st.session_state: st.session_state.lat = 47.3769 # Zurich
if 'lon' not in st.session_state: st.session_state.lon = 8.5417
if 'analysis_result' not in st.session_state: st.session_state.analysis_result = None
if 'story_mode' not in st.session_state: st.session_state.story_mode = False

# ---------------------------------------------------------
# HEADER & INPUT
# ---------------------------------------------------------
st.title("GeoPlant")

with st.container():
    c1, c2 = st.columns([1, 2])

    with c1:
        st.markdown("### Choose the plant you wish to grow")
        # Versuch DB Abfrage, sonst Fallback Liste
        try:
            plant_list = backend_api.get_plant_list()
            if not plant_list: raise Exception("Empty DB")
        except:
            plant_list = charts_example_data.plants

        selected_plant = st.selectbox("Ich möchte anbauen:", plant_list)

    with c2:
        st.markdown("### Choose a location for your plant's potential future home")
        m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=5, height=250)
        folium.Marker([st.session_state.lat, st.session_state.lon], icon=folium.Icon(color="green", icon="leaf")).add_to(m)
        map_out = st_folium(m, height=250, use_container_width=True)

        if map_out['last_clicked']:
            st.session_state.lat = map_out['last_clicked']['lat']
            st.session_state.lon = map_out['last_clicked']['lng']
            st.rerun()

    st.markdown("---")
    if st.button("Start Data Story", type="primary", use_container_width=True):
        with st.spinner(f"Analysiere Daten für {selected_plant}..."):
            # Backend Call
            st.session_state.analysis_result = backend_api.analyze_suitability(
                selected_plant, st.session_state.lat, st.session_state.lon
            )
            st.session_state.story_mode = True
            st.rerun()

# ---------------------------------------------------------
# DATA STORY
# ---------------------------------------------------------
if st.session_state.story_mode and st.session_state.analysis_result:
    res = st.session_state.analysis_result

    # Prüfen ob Fehler im Backend Resultat waren (z.B. Ocean)
    # Wenn "error" drin ist, setzen wir real_data auf None -> Charts nutzen Fallback
    if "error" in res:
        st.warning(f"Achtung: {res['error']} - Zeige Simulationsdaten.")
        real_data_for_charts = None
    else:
        real_data_for_charts = res

    # --- KAPITEL 1: RADAR CHART ---
    st.markdown('<div class="story-step">', unsafe_allow_html=True)
    st.markdown(f'<div class="story-title">Kapitel 1: Der Fingerabdruck</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="story-text">Vergleich der lokalen Bedingungen mit den Idealwerten von <b>{selected_plant}</b>.</div>', unsafe_allow_html=True)

    # Hier übergeben wir nun die echten Daten (oder None)
    fig_radar = create_radar_chart(selected_plant, "Selected Location", real_data=real_data_for_charts)

    col_c1, col_c2, col_c3 = st.columns([1,3,1])
    with col_c2: st.plotly_chart(fig_radar, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


    # --- KAPITEL 2: DIVERGING BAR ---
    st.markdown('<div class="story-step">', unsafe_allow_html=True)
    st.markdown(f'<div class="story-title">Kapitel 2: Die Lücken</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="story-text">Wo genau weicht das Klima vom Ideal ab?</div>', unsafe_allow_html=True)

    fig_div = create_diverging_bar_chart(selected_plant, "Selected Location", real_data=real_data_for_charts)

    col_c1, col_c2, col_c3 = st.columns([1,3,1])
    with col_c2: st.plotly_chart(fig_div, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


    # --- KAPITEL 3: BUBBLE MAP ---
    st.markdown('<div class="story-step">', unsafe_allow_html=True)
    st.markdown(f'<div class="story-title">Kapitel 3: Globale Perspektive</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="story-text">Wo auf der Welt (aus unserer Datenbank) würde diese Pflanze sonst noch wachsen?</div>', unsafe_allow_html=True)

    # Bubble Map nutzt immer Mock Data für Global Context (siehe charts.py)
    fig_map = create_bubble_map(selected_plant)

    st.plotly_chart(fig_map, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


    # --- FINAL DASHBOARD ---
    st.markdown('<div class="dashboard-container">', unsafe_allow_html=True)
    st.subheader(f"Dashboard {selected_plant}")

    # Metriken (Score kommt immer aus dem Backend Result, wenn vorhanden)
    score = res.get('score', 0)
    status = res.get('status', 'Simulation')

    m1, m2, m3 = st.columns(3)
    m1.metric("Suitability Score", f"{score}/100", delta=status)
    m2.caption("Datenquelle: CHELSA V2.1 (Raster 1km)")

    st.divider()

    r1, r2 = st.columns(2)
    with r1: st.plotly_chart(fig_radar, use_container_width=True, key="d_radar")
    with r2: st.plotly_chart(fig_div, use_container_width=True, key="d_div")

    st.markdown('</div>', unsafe_allow_html=True)
