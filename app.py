import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import backend_api
from charts import create_radar_chart, create_diverging_bar_chart

st.set_page_config(page_title="GeoPlant", layout="wide", page_icon="🌱")

# CSS
st.markdown(
    """
<style>
:root { --c-dark-blue: #1162AC; --c-pink: #F15CE3; --c-yellow: #DAFF15; }
h1 { color: var(--c-dark-blue); font-weight: 900; }
.pop-card { border: 3px solid black; padding: 20px; border-radius: 15px; box-shadow: 5px 5px 0px black; margin-bottom: 20px; }
.pop-card-yellow { background-color: var(--c-yellow); color: black; border: 3px solid black; padding: 20px; border-radius: 15px; }
</style>
""",
    unsafe_allow_html=True,
)

# Session State
if "lat" not in st.session_state:
    st.session_state.lat = 47.3769
if "lon" not in st.session_state:
    st.session_state.lon = 8.5417
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "regional_scan" not in st.session_state:
    st.session_state.regional_scan = pd.DataFrame()

# HEADER
st.markdown(
    """
<div class="pop-card-yellow" style="text-align: center; margin-bottom: 2rem;">
    <h1 style="margin:0; font-size: 4rem;">G E O P L A N T</h1>
    <div style="font-weight:700; letter-spacing:3px;">REAL-TIME DATABASE ANALYTICS</div>
</div>
""",
    unsafe_allow_html=True,
)

# INPUTS
with st.container():
    st.markdown('<div class="pop-card">', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 2], gap="large")

    with c1:
        st.markdown("### 1. SELECT CROP")
        try:
            plant_list = backend_api.get_plant_list()
        except:
            plant_list = []
        if not plant_list:
            st.error("Database Empty")
            st.stop()
        selected_plant = st.selectbox("Plant:", plant_list)

    with c2:
        st.markdown("### 2. PICK LOCATION")
        m = folium.Map(
            location=[st.session_state.lat, st.session_state.lon],
            zoom_start=5,
            height=250,
        )
        folium.Marker(
            [st.session_state.lat, st.session_state.lon],
            icon=folium.Icon(color="green", icon="leaf"),
        ).add_to(m)
        map_out = st_folium(m, height=250, use_container_width=True)
        if map_out["last_clicked"]:
            st.session_state.lat = map_out["last_clicked"]["lat"]
            st.session_state.lon = map_out["last_clicked"]["lng"]
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("🚀 RUN ANALYSIS", type="primary", use_container_width=True):
        with st.spinner("Querying Database..."):
            # 1. Analyze Point
            res = backend_api.analyze_suitability(
                selected_plant, st.session_state.lat, st.session_state.lon
            )
            st.session_state.analysis_result = res

            # 2. Scan Region (25 points)
            if "error" not in res:
                st.session_state.regional_scan = backend_api.scan_region(
                    selected_plant, st.session_state.lat, st.session_state.lon
                )
            st.rerun()

# RESULTS
if st.session_state.analysis_result:
    res = st.session_state.analysis_result

    if "error" in res:
        st.error(res["error"])
    else:
        score = res["score"]
        climate = res["climate"]
        plant = res["plant"]

        # --- SCORE CARD ---
        color = "#2ECC71" if score > 50 else "#E74C3C"
        st.markdown(
            f"""
        <div class="pop-card" style="text-align:center; background-color:{color};">
            <h2 style="color:white; margin:0;">SUITABILITY: {score}/100</h2>
            <div style="color:white; font-size:1.2rem;">{res['status']}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # --- DATA DEBUGGER (Prove it works) ---
        with st.expander("🔎 View Raw Database Data (Click to Expand)"):
            st.write("This data was pulled from the 50GB Raster Database just now:")
            st.json(climate)
            st.write(f"**Plant Needs:** Min Temp > {plant['Min_Temp']}°C")

        # --- CHARTS ---
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(
                create_radar_chart(selected_plant, "Loc", res), use_container_width=True
            )
        with c2:
            st.plotly_chart(
                create_diverging_bar_chart(selected_plant, "Loc", res),
                use_container_width=True,
            )

        # --- REGIONAL MAP (FIXED) ---
        st.markdown("### 🗺️ Regional Hotspot Scanner")
        st.caption(
            "We scanned 25 points (~200km radius) around your location to find better spots."
        )

        if not st.session_state.regional_scan.empty:
            # We use st.map which is native and robust
            st.map(
                st.session_state.regional_scan,
                latitude="lat",
                longitude="lon",
                size="size",
                color="color",
            )
        else:
            st.warning("Could not scan region (Ocean or missing data).")
