import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import backend_api
from charts import (
    create_radar_chart,
    create_diverging_bar_chart,
    create_top_countries_chart,
    create_circular_gauge,
)

st.set_page_config(page_title="GeoPlant", layout="wide", page_icon="🌱")

# ---------------------------------------------------------
# CSS & STYLING
# ---------------------------------------------------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700;900&family=Poppins:wght@400;600&display=swap');

html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }
:root { --c-dark-blue: #1162AC; --c-pink: #F15CE3; --c-yellow: #DAFF15; --c-med-blue: #1F89D8; }

h1 { font-family: 'Montserrat', sans-serif !important; font-weight: 900 !important; color: var(--c-dark-blue); text-shadow: 2px 2px 0px var(--c-yellow); text-transform: uppercase; }

/* Headers and Cards that contain only Text work fine */
.pop-card-yellow { background: var(--c-yellow); color: black; border: 3px solid black; padding: 20px; border-radius: 15px; box-shadow: 5px 5px 0px black; }

.stButton > button { background: var(--c-pink); color: white; border: 3px solid black; font-weight: 900; box-shadow: 4px 4px 0px 0px #000000; text-transform: uppercase; }
.stButton > button:hover { transform: translate(2px, 2px); box-shadow: 2px 2px 0px 0px #000000; color:white; border-color:black; }
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

# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------
st.markdown(
    """
<div class="pop-card-yellow" style="text-align: center; margin-bottom: 2rem;">
    <h1 style="margin:0; font-size: 4rem;">G E O P L A N T</h1>
    <div style="font-weight:700; letter-spacing:3px;">GLOBAL CROP ANALYTICS DASHBOARD</div>
</div>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# INPUT SECTION
# ---------------------------------------------------------
with st.container():
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
        # Input Map (Folium - Clean Tiles)
        m = folium.Map(
            location=[st.session_state.lat, st.session_state.lon],
            zoom_start=4,
            tiles="CartoDB positron",
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

    if st.button("🚀 RUN GLOBAL ANALYSIS", type="primary", use_container_width=True):
        with st.spinner("Scanning 190+ Countries..."):
            # 1. Analyze Point
            res = backend_api.analyze_suitability(
                selected_plant, st.session_state.lat, st.session_state.lon
            )
            st.session_state.analysis_result = res

            # 2. Global Scan
            if "error" not in res:
                st.session_state.regional_scan = backend_api.scan_continent_heatmap(
                    selected_plant, 0, 0
                )
            st.rerun()

# ---------------------------------------------------------
# RESULTS
# ---------------------------------------------------------
if st.session_state.analysis_result:
    res = st.session_state.analysis_result

    if "error" in res:
        st.error(res["error"])
    else:
        score = res["score"]

        # --- ROW 1: CHARTS (Gauge | Radar | Diverging Bar) ---
        # Adjusted columns to fit 3 charts side-by-side
        c1, c2, c3 = st.columns([1, 1, 1])

        with c1:
            # Suitability Gauge
            st.plotly_chart(
                create_circular_gauge(score, real_data=res, height=300),
                use_container_width=True,
            )

        with c2:
            # Radar Chart
            st.plotly_chart(
                create_radar_chart(selected_plant, "Loc", res, height=300),
                use_container_width=True,
            )

        with c3:
            # Diverging Bar Chart
            st.plotly_chart(
                create_diverging_bar_chart(selected_plant, "Loc", res, height=300),
                use_container_width=True,
            )

        st.divider()

        # --- ROW 2: MAP & TOP LIST ---
        # Map on Left (Wide), Top Regions on Right (Narrow)
        if not st.session_state.regional_scan.empty:
            m1, m2 = st.columns([2, 1])

            with m1:
                st.markdown("### GLOBAL MAP")
                scan_df = st.session_state.regional_scan

                m_global = folium.Map(
                    location=[20, 0], zoom_start=2, tiles="CartoDB positron"
                )

                folium.Choropleth(
                    geo_data="https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/world-countries.json",
                    name="Score",
                    data=scan_df,
                    columns=["country", "score"],
                    key_on="feature.properties.name",
                    fill_color="Greens",
                    fill_opacity=0.8,
                    line_opacity=0.2,
                    legend_name="Suitability Score (0-100)",
                    bins=[0, 20, 40, 60, 80, 100],
                    nan_fill_color="#f0f0f0",
                    highlight=True,
                ).add_to(m_global)
                st_folium(m_global, height=500, use_container_width=True)

            with m2:
                st.markdown("### TOP REGIONS")
                top = backend_api.get_top_countries(
                    selected_plant, st.session_state.regional_scan
                )
                # Height matched to map for better alignment
                st.plotly_chart(
                    create_top_countries_chart(top, height=500),
                    use_container_width=True,
                )
