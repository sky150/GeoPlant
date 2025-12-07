import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import os

# local
import backend_api
from charts import create_radar_chart, create_diverging_bar_chart, create_bubble_map
import charts_example_data

# ---------------------------------------------------------
# 1. PAGE CONFIG
# ---------------------------------------------------------
st.set_page_config(page_title="GeoPlant Analytics", layout="wide", page_icon="🌱")

# ---------------------------------------------------------
# 2. STYLING SETUP
# ---------------------------------------------------------
COLORS = {
    "C_DARK_BLUE": "#1162AC",
    "C_MED_BLUE": "#1F89D8",
    "C_PINK": "#F15CE3",
    "C_YELLOW": "#DAFF15",
    "C_LIME": "#BDD409"
}

def load_css(file_name):
    if not os.path.exists(file_name):
        st.error(f"⚠️ CSS Datei nicht gefunden: {file_name}.")
        return

    css_vars = ":root {\n"
    for name, code in COLORS.items():
        css_var_name = f"--{name.lower().replace('_', '-')}"
        css_vars += f"    {css_var_name}: {code};\n"
    css_vars += "}\n"

    with open(file_name) as f:
        css_content = f.read()

    st.markdown(f'<style>{css_vars}{css_content}</style>', unsafe_allow_html=True)

load_css("style.css")

# ---------------------------------------------------------
# 3. SESSION STATE
# ---------------------------------------------------------
if 'lat' not in st.session_state: st.session_state.lat = 47.3769
if 'lon' not in st.session_state: st.session_state.lon = 8.5417
if 'analysis_result' not in st.session_state: st.session_state.analysis_result = None
if 'story_mode' not in st.session_state: st.session_state.story_mode = False

# ---------------------------------------------------------
# 4. HEADER & INPUT
# ---------------------------------------------------------

# NEU: Integrierter Header in der gelben Pop-Card
# Dein Text: "G E O P L A N T" und "THE ANALYTICS TOOL FOR FUTURE FARMING"
st.markdown(f"""
<div class="pop-card-yellow" style="text-align: center; padding: 40px; margin-bottom: 2rem;">
    <h1 style="font-size: 5rem; margin: 0; line-height: 1; color: var(--c-dark-blue); text-shadow: 4px 4px 0px white;">
        G E O P L A N T
    </h1>
    <div style="font-size: 1.2rem; font-weight: 700; color: black; letter-spacing: 3px; margin-top: 15px;">
        THE ANALYTICS TOOL FOR FUTURE FARMING
    </div>
</div>
""", unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="pop-card">', unsafe_allow_html=True)

    c1, c2 = st.columns([1, 2], gap="large")

    with c1:
        st.markdown(f"<h3 style='color:black;'>1. CHOOSE PLANT</h3>", unsafe_allow_html=True)
        try:
            plant_list = backend_api.get_plant_list()
            if not plant_list: raise Exception("Empty DB")
        except:
            plant_list = charts_example_data.plants

        selected_plant = st.selectbox("I would like to grow:", plant_list)
        st.markdown("<br>", unsafe_allow_html=True)

    with c2:
        st.markdown(f"<h3 style='color:black;'>2. PICK LOCATION</h3>", unsafe_allow_html=True)

        m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=5, height=250)
        folium.Marker(
            [st.session_state.lat, st.session_state.lon],
            icon=folium.Icon(color="black", icon="leaf", icon_color="#DAFF15")
        ).add_to(m)

        map_out = st_folium(m, height=250, use_container_width=True)

        if map_out['last_clicked']:
            st.session_state.lat = map_out['last_clicked']['lat']
            st.session_state.lon = map_out['last_clicked']['lng']
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    col_btn1, col_btn2, col_btn3 = st.columns([1,2,1])
    with col_btn2:
        st.markdown("<br>", unsafe_allow_html=True)
        # Dein Button Text ohne Emoji
        if st.button("START DATA STORY", type="primary", use_container_width=True):
            # Dein Spinner Text
            with st.spinner(f"Analysing Data for {selected_plant}..."):
                st.session_state.analysis_result = backend_api.analyze_suitability(
                    selected_plant, st.session_state.lat, st.session_state.lon
                )
                st.session_state.story_mode = True
                st.rerun()

# ---------------------------------------------------------
# 5. DATA STORY
# ---------------------------------------------------------
if st.session_state.story_mode and st.session_state.analysis_result:
    res = st.session_state.analysis_result

    if "error" in res:
        st.warning(f"FYI: {res['error']} - Sample data story due to data import failure.")
        real_data_for_charts = None
    else:
        real_data_for_charts = res

    spacer = '<div style="margin-top: 5rem;"></div>'

    # --- KAPITEL 1 ---
    st.markdown(spacer, unsafe_allow_html=True)

    # Dein Text & Title
    st.markdown(f"""
    <div class="pop-card-yellow" style="text-align: center; margin-bottom: 2rem;">
        <div class="story-title"><b>Comparing conditions</div>
        <div class="story-text" style="background:white; display:inline-block;">
            How does <b>{selected_plant}</b> fit in <b>{"Selected Location"}</b>.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Standard Größe für Story (height=500)
    fig_radar = create_radar_chart(selected_plant, "Selected Location", real_data=real_data_for_charts, height=500)
    c1, c2, c3 = st.columns([1,4,1])
    with c2: st.plotly_chart(fig_radar, use_container_width=True)


    # --- KAPITEL 2 ---
    st.markdown(spacer, unsafe_allow_html=True)

    # Dein Text & Title
    st.markdown(f"""
    <div class="pop-card-yellow" style="text-align: center; margin-bottom: 2rem;">
        <div class="story-title">Targeting parameters</div>
        <div class="story-text" style="background:white; display:inline-block;">
            A detailed look on (un)matching parameters.
        </div>
    </div>
    """, unsafe_allow_html=True)

    fig_div = create_diverging_bar_chart(selected_plant, "Selected Location", real_data=real_data_for_charts, height=450)
    c1, c2, c3 = st.columns([1,4,1])
    with c2: st.plotly_chart(fig_div, use_container_width=True)


    # --- KAPITEL 3 ---
    st.markdown(spacer, unsafe_allow_html=True)

    # Dein Text & Title
    st.markdown(f"""
    <div class="pop-card-yellow" style="text-align: center; margin-bottom: 2rem;">
        <div class="story-title">Spotting the comfort zone</div>
        <div class="story-text" style="background:white; display:inline-block;">
            Locations for your plants best growth conditions.
        </div>
    </div>
    """, unsafe_allow_html=True)

    fig_map = create_bubble_map(selected_plant, height=500)
    st.plotly_chart(fig_map, use_container_width=True)

    st.markdown(spacer, unsafe_allow_html=True)


    # --- FINAL DASHBOARD ---
    # Layout Optimierung: Charts nebeneinander (klein), Map darunter (breit)

    st.markdown(f"""
    <div class="pop-card" style="background-color:{COLORS['C_LIME']}; border-color:black; margin-bottom:20px;">
        <h2 style="text-align:center; color:black; margin:0;">Dashboard: {selected_plant.upper()}</h2>
    </div>
    """, unsafe_allow_html=True)

    score = res.get('score', 0)
    status = res.get('status', 'Simulation')

    # 1. Row: Metrics (Dein Text)
    m1, m2, m3 = st.columns(3)

    with m1:
        st.markdown(f"""
        <div class="pop-card" style="text-align:center; padding:15px;">
            <div style="font-weight:bold;">Suitability Score</div>
            <div style="font-size:3rem; font-weight:900; color:{COLORS['C_DARK_BLUE']}; text-shadow: 2px 2px 0px {COLORS['C_PINK']};">
                {score}/100
            </div>
            <div style="background:black; color:white; padding:2px 8px; border-radius:10px; display:inline-block;">{status}</div>
        </div>
        """, unsafe_allow_html=True)

    with m2:
         st.markdown(f"""
        <div class="pop-card" style="text-align:center; padding:15px; background-color:{COLORS['C_MED_BLUE']}; color:white;">
            <div style="font-weight:bold;">Data Source</div>
            <br>
            <div style="font-size:1.5rem; font-weight:900;">Chelsa 2.1</div>
            <div>High Res (1km)</div>
        </div>
        """, unsafe_allow_html=True)

    with m3:
         st.markdown(f"""
        <div class="pop-card" style="text-align:center; padding:15px; background-color:{COLORS['C_PINK']}; color:white;">
            <div style="font-weight:bold;">Next Steps</div>
            <br>
            <div style="font-size:1.5rem; font-weight:900;">Export</div>
            <div>PDF Report</div>
        </div>
        """, unsafe_allow_html=True)

    # 2. Row: Radar & Bar Chart nebeneinander (Verkleinert auf 300px Höhe)
    d_c1, d_c2 = st.columns(2)

    # Neue, kleinere Chart-Instanzen generieren
    dash_fig_radar = create_radar_chart(selected_plant, "", real_data_for_charts, height=300)
    dash_fig_div = create_diverging_bar_chart(selected_plant, "", real_data_for_charts, height=300)

    with d_c1:
        st.markdown('<div class="pop-card" style="padding:10px;">', unsafe_allow_html=True)
        st.plotly_chart(dash_fig_radar, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

    with d_c2:
        st.markdown('<div class="pop-card" style="padding:10px;">', unsafe_allow_html=True)
        st.plotly_chart(dash_fig_div, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

    # 3. Row: Map (Volle Breite, Höhe 350px)
    dash_fig_map = create_bubble_map(selected_plant, height=350)

    st.markdown('<div class="pop-card" style="padding:10px;">', unsafe_allow_html=True)
    st.plotly_chart(dash_fig_map, use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)
