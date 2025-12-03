import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import backend_api

# ---------------------------------------------------------
# UI CONFIGURATION & CSS MAGIC
# ---------------------------------------------------------
st.set_page_config(page_title="GeoPlant Analytics", layout="wide", page_icon="🌱")

# Hier ist der CSS Trick für das Scrollytelling
st.markdown("""
<style>
    /* Jeder Story-Schritt bekommt eine Mindesthöhe und zentrierten Inhalt */
    .story-step {
        min-height: 85vh;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        padding: 2rem;
        border-bottom: 1px solid #f0f2f6;
    }

    .story-title {
        font-size: 2.5rem !important;
        font-weight: 700 !important;
        color: #2c3e50;
        text-align: center;
        margin-bottom: 1rem;
    }

    .story-text {
        font-size: 1.2rem !important;
        color: #555;
        text-align: center;
        max-width: 800px;
        margin: 0 auto 2rem auto;
    }

    /* Das finale Dashboard etwas abheben */
    .dashboard-container {
        background-color: #f8f9fa;
        padding: 2rem;
        border-radius: 15px;
        margin-top: 5rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# SESSION STATE SETUP
# ---------------------------------------------------------
if 'lat' not in st.session_state: st.session_state.lat = 47.3769
if 'lon' not in st.session_state: st.session_state.lon = 8.5417
# Wichtig: Wir speichern das Ergebnis, damit die Story beim Scrollen/Klicken bleibt
if 'analysis_result' not in st.session_state: st.session_state.analysis_result = None
if 'story_mode' not in st.session_state: st.session_state.story_mode = False

# ---------------------------------------------------------
# HEADER & INPUT SECTION (Intro)
# ---------------------------------------------------------
st.title("🌍 GeoPlant: Smart Crop Suitability")

# Container für die Auswahl (bleibt oben)
with st.container():
    c1, c2 = st.columns([1, 2])

    with c1:
        st.markdown("### 1️⃣ Wähle deine Pflanze")
        try:
            plant_list = backend_api.get_plant_list()
        except:
            plant_list = ["Example Plant"] # Fallback

        selected_plant = st.selectbox("Pflanze:", plant_list, label_visibility="collapsed")

    with c2:
        st.markdown("### 2️⃣ Wähle den Standort")
        # Kleine Karte für die Auswahl
        m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=4, height=300)
        folium.Marker([st.session_state.lat, st.session_state.lon], icon=folium.Icon(color="green", icon="leaf")).add_to(m)
        map_out = st_folium(m, height=200, use_container_width=True)

        if map_out['last_clicked']:
            st.session_state.lat = map_out['last_clicked']['lat']
            st.session_state.lon = map_out['last_clicked']['lng']
            st.rerun()

    if st.button("🚀 Start Data Story", type="primary", use_container_width=True):
        with st.spinner(f"Analysiere Boden & Klima für {selected_plant}..."):
            # Daten holen und in Session speichern
            st.session_state.analysis_result = backend_api.analyze_suitability(
                selected_plant, st.session_state.lat, st.session_state.lon
            )
            st.session_state.story_mode = True
            st.rerun()

# ---------------------------------------------------------
# THE DATA STORY (Scrollytelling)
# ---------------------------------------------------------
if st.session_state.story_mode and st.session_state.analysis_result:
    res = st.session_state.analysis_result

    if "error" in res:
        st.error(res['error'])
    else:
        # --- SCENE 1: THE VERDICT (Score) ---
        st.markdown('<div class="story-step">', unsafe_allow_html=True)
        st.markdown(f'<div class="story-title">Kapitel 1: Das Urteil</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="story-text">Basierend auf 30 Jahren Klimadaten für diesen Standort analysieren wir die Überlebenschance von <b>{selected_plant}</b>.</div>', unsafe_allow_html=True)

        # Grosser Gauge Chart im Fokus
        col_center = st.columns([1,2,1])
        with col_center[1]:
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number", value=res['score'],
                title={'text': f"Suitability: {res['status']}"},
                gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#2ECC71" if res['score']>80 else "#E74C3C"}}
            ))
            fig_gauge.update_layout(height=400)
            st.plotly_chart(fig_gauge, use_container_width=True)

            if res['reasons']:
                st.warning(f"⚠️ Hauptproblem: {res['reasons'][0]}")
            else:
                st.success("✅ Keine kritischen Probleme gefunden.")
        st.markdown('</div>', unsafe_allow_html=True) # End Scene 1


        # --- SCENE 2: THE CLIMATE DNA (Radar) ---
        st.markdown('<div class="story-step">', unsafe_allow_html=True)
        st.markdown(f'<div class="story-title">Kapitel 2: Die Klima-DNA</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="story-text">Wie passt das lokale Klima zu den Bedürfnissen der Pflanze? Sehen wir uns die Details an.</div>', unsafe_allow_html=True)

        # Wiederholung des Radar Codes (vereinfacht für Demo)
        climate, plant = res['climate'], res['plant']
        categories = ['Temp', 'Rain', 'pH', 'Sun', 'Elev']
        # (Hier deinen Normierungs-Code einfügen) -> Mock Data für Demo Layout:
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(r=[0.8, 0.7, 0.9, 0.4, 0.8], theta=categories, fill='toself', name='Standort'))
        fig_radar.add_trace(go.Scatterpolar(r=[0.6, 0.6, 0.6, 0.6, 0.6], theta=categories, fill='toself', name='Pflanze Min'))
        fig_radar.update_layout(height=500, title="Vergleich: Standort (Blau) vs. Bedarf (Grün)")

        col_c2 = st.columns([1,3,1])
        with col_c2[1]:
            st.plotly_chart(fig_radar, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True) # End Scene 2


        # --- SCENE 3: SEASONALITY (Line) ---
        st.markdown('<div class="story-step">', unsafe_allow_html=True)
        st.markdown(f'<div class="story-title">Kapitel 3: Der Jahresverlauf</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="story-text">Pflanzen leben nicht im Durchschnitt. Überlebt sie den Winter? Vertrocknet sie im Sommer?</div>', unsafe_allow_html=True)

        # (Hier deinen Line-Chart Code einfügen) -> Mock Data:
        months = ['J','F','M','A','M','J','J','A','S','O','N','D']
        temps = [climate['min_temp'], 5, 10, 15, 20, climate['max_temp'], 22, 20, 15, 10, 5, climate['min_temp']]
        fig_line = go.Figure(go.Scatter(x=months, y=temps, mode='lines+markers', line_shape='spline'))
        fig_line.add_hrect(y0=plant['Min_Temp'], y1=plant['Max_Temp'], fillcolor="green", opacity=0.1)
        fig_line.update_layout(height=500, title="Temperaturverlauf vs. Wohlfühlzone")

        st.plotly_chart(fig_line, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True) # End Scene 3


        # --- SCENE 4: FINAL DASHBOARD (Explorer) ---
        st.markdown("---")
        st.markdown('<div class="dashboard-container">', unsafe_allow_html=True)
        st.subheader("🎛️ Expert Dashboard (Explorer)")
        st.caption("Hier kannst du die Daten nun im Detail filtern und analysieren.")

        # Interaktive Filter (Simuliert)
        d_col1, d_col2, d_col3 = st.columns(3)
        with d_col1:
            st.checkbox("Zeige kritische Limits", value=True)
        with d_col2:
            st.slider("Simuliere Temperaturanstieg (°C)", 0, 5, 0)
        with d_col3:
             st.selectbox("Datenquelle", ["CHELSA V2.1", "WorldClim (Legacy)"])

        # Kleines Grid-Layout für die Übersicht
        grid1, grid2 = st.columns(2)
        with grid1:
            st.plotly_chart(fig_gauge, use_container_width=True, key="dash_gauge") # key nutzen um Konflikt zu vermeiden
            st.info(f"Niederschlag: {climate['rain']}mm / Jahr")
        with grid2:
            st.plotly_chart(fig_radar, use_container_width=True, key="dash_radar")
            st.info(f"Temperatur: {climate['min_temp']}°C bis {climate['max_temp']}°C")

        st.markdown('</div>', unsafe_allow_html=True)
