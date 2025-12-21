import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import streamlit.components.v1 as components
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

h1 { font-family: 'Montserrat', sans-serif !important; font-weight: 900 !important; color: var(--c-dark-blue); text-transform: uppercase; }

/* 1. AUTO-STYLE PLOTLY CHARTS AS CARDS */
.stPlotlyChart {
    background-color: white;
    border: 3px solid black;
    border-radius: 15px;
    box-shadow: 5px 5px 0px 0px #000000;
    padding: 10px;
    margin-bottom: 20px;
}

/* 2. AUTO-STYLE FOLIUM MAP AS CARD */
iframe {
    border: 3px solid black !important;
    border-radius: 15px !important;
    box-shadow: 5px 5px 0px 0px #000000 !important;
    background-color: white;
    padding: 5px;
}

/* 3. CARD STYLING */
.pop-card {
    background: white;
    border: 3px solid black;
    border-radius: 15px;
    padding: 15px;
    box-shadow: 5px 5px 0px 0px #000000;
    margin-bottom: 20px;
}

.pop-card h3 {
    font-family: 'Montserrat', sans-serif;
    font-weight: 900;
    color: #333;
    font-size: 1rem;
    text-transform: uppercase;
}

/* 4. STATS LAYOUT (New classes for the cards) */
.stat-container { display: flex; justify-content: space-between; text-align: left; gap: 25px; }
.stat-item { width: 32%; }
.stat-label { font-size: 0.8rem; color: #666; font-weight: 600; text-transform: uppercase; margin-bottom: 4px; }
.stat-value { font-size: 1.1rem; font-weight: 700; color: black; }
.stat-sub { font-size: 0.75rem; color: #999; margin-top: 2px; }

.stButton > button { background: var(--c-pink); color: white; border: 3px solid black; font-weight: 900; box-shadow: 4px 4px 0px 0px #000000; text-transform: uppercase; }
.stButton > button:hover { transform: translate(2px, 2px); box-shadow: 2px 2px 0px 0px #000000; color:white; border-color:black; }

/* Centered Section Titles */
.chart-title {
    text-align: center;
    font-family: 'Montserrat', sans-serif;
    font-weight: 900;
    margin-bottom: 10px;
    text-transform: uppercase;
    color: #333;

}
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
<div style="text-align: center; margin-bottom: 3rem;">
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
        st.markdown("### 1. SELECT PLANT")
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

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("RUN GLOBAL ANALYSIS", type="primary", use_container_width=True):
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
        plant = res["plant"]
        climate = res["climate"]

        st.divider()
        # --- NEW: KPI LAYER (Crop Info & Climate Summary) ---
        k1, k2 = st.columns(2)

        with k1:
            st.markdown(
                f"""
            <div class="pop-card">
                <h3>Crop Requirements: {plant['name']}</h3>
                <div class="stat-container">
                    <div class="stat-item">
                        <div class="stat-label">Optimal Temp</div>
                        <div class="stat-value">{plant['Min_Temp']}°C to {plant['Max_Temp']}°C</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Water Demand</div>
                        <div class="stat-value">{plant['Min_Rain']} - {plant['Max_Rain']} mm</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Soil pH</div>
                        <div class="stat-value">{plant['Min_pH']} - {plant['Max_pH']}</div>
                    </div>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with k2:
            st.markdown(
                f"""
            <div class="pop-card">
                <h3>Location Climate Summary</h3>
                <div class="stat-container">
                    <div class="stat-item">
                        <div class="stat-label">Winter Low</div>
                        <div class="stat-value">{climate['min_temp']}°C</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Summer High</div>
                        <div class="stat-value">{climate['max_temp']}°C</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Annual Rain</div>
                        <div class="stat-value">{climate['rain']} mm</div>
                    </div>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        # --- ROW 1: CHARTS (3 Cols) ---
        c1, c2, c3 = st.columns([1, 1, 1])

        with c1:
            st.plotly_chart(
                create_circular_gauge(score, real_data=res, height=320),
                use_container_width=True,
            )

        with c2:
            st.plotly_chart(
                create_radar_chart(selected_plant, "Loc", res, height=320),
                use_container_width=True,
            )

        with c3:
            st.plotly_chart(
                create_diverging_bar_chart(selected_plant, "Loc", res, height=320),
                use_container_width=True,
            )

        # Removed the divider line between top charts and map section

        # --- ROW 2: MAP & TOP LIST ---
        m1, m2 = st.columns([2.7, 1])

        if not st.session_state.regional_scan.empty:
            with m1:
                scan_df = st.session_state.regional_scan

                # Karte initialisieren (No Labels)
                m_global = folium.Map(
                    location=[20, 0],
                    zoom_start=2,
                    tiles="https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png",
                    attr="CartoDB",
                )

                # --- 1. INJECT TITLE (Floating Inside Card) ---
                title_html = """
                <div style="
                    position: fixed; top: 15px; left: 50%; transform: translateX(-50%);
                    z-index: 1000; background-color: white; padding: 5px 15px;
                    border: 2px solid black; border-radius: 10px;
                    font-family: 'Montserrat', sans-serif; font-weight: 900;
                    font-size: 16px; color: #333; box-shadow: 3px 3px 0px black;">
                    GLOBAL MAP
                </div>
                """
                m_global.get_root().html.add_child(folium.Element(title_html))

                # --- 2. INJECT LEGEND (Floating Bottom Left) ---
                legend_html = """
                <div style="
                    position: fixed; bottom: 20px; left: 20px; z-index: 1000;
                    background-color: white; padding: 10px; border: 2px solid black;
                    border-radius: 10px; font-family: 'Poppins', sans-serif;
                    box-shadow: 3px 3px 0px black; font-size: 12px;">
                    <div style="margin-bottom: 5px; font-weight: bold; text-align:center;">SUITABILITY</div>
                    <div style="display:flex; align-items:center; margin-bottom:3px;">
                        <span style="background:#BDD409; width:15px; height:15px; display:inline-block; border:1px solid black; margin-right:5px;"></span> High (>75)
                    </div>
                    <div style="display:flex; align-items:center; margin-bottom:3px;">
                        <span style="background:#1F89D8; width:15px; height:15px; display:inline-block; border:1px solid black; margin-right:5px;"></span> Medium (75-45)
                    </div>
                    <div style="display:flex; align-items:center;">
                        <span style="background:#E6A8D7; width:15px; height:15px; display:inline-block; border:1px solid black; margin-right:5px;"></span> Low (<45)
                    </div>
                </div>
                """
                m_global.get_root().html.add_child(folium.Element(legend_html))

                # --- CUSTOM COLOR LOGIC ---
                score_dict = scan_df.set_index("country")["score"].to_dict()

                def style_function(feature):
                    country_name = feature["properties"]["name"]
                    score = score_dict.get(country_name, None)
                    fill_color = "#f0f0f0"

                    if score is not None:
                        if score >= 75:
                            fill_color = "#BDD409"  # C_LIME
                        elif score >= 45:
                            fill_color = "#1F89D8"  # C_MED_BLUE
                        else:
                            fill_color = "#E6A8D7"  # C_PINK

                    return {
                        "fillColor": fill_color,
                        "color": "black",
                        "weight": 1,
                        "fillOpacity": 0.8,
                    }

                folium.GeoJson(
                    "https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/world-countries.json",
                    name="Suitability",
                    style_function=style_function,
                    tooltip=folium.GeoJsonTooltip(
                        fields=["name"],
                        aliases=["Country:"],
                        style="font-family: Poppins; font-size: 14px;",
                    ),
                ).add_to(m_global)

                map_html = m_global.get_root().render()

                # This replacement forces the body inside the iframe to have 0 margin,
                # so the map touches the card borders perfectly.
                map_html = map_html.replace(
                    "</head>",
                    "<style>html, body {width: 100%; height: 100%; margin: 0; padding: 0;}</style></head>",
                )

                # Render with components.html (Height 500 matches the card layout)
                components.html(map_html, height=525)
            with m2:
                top = backend_api.get_top_countries(
                    selected_plant, st.session_state.regional_scan
                )
                st.plotly_chart(
                    create_top_countries_chart(top, height=500),
                    use_container_width=True,
                )
