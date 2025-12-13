import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import backend_api
from charts import (
    create_radar_chart,
    create_circular_gauge,
    create_top_countries_chart,
    create_diverging_bar_chart,
)

st.set_page_config(page_title="GeoPlant", layout="wide", page_icon="🌱")

# ORIGINAL CSS FROM GITHUB
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700;900&family=Poppins:wght@400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Poppins', sans-serif;
    color: #000000;
}

:root { 
    --c-dark-blue: #1162AC; 
    --c-pink: #F15CE3; 
    --c-yellow: #DAFF15; 
    --c-med-blue: #1F89D8;
    --c-lime: #BDD409;
}

h1, h2, h3 {
    font-family: 'Montserrat', sans-serif !important;
    font-weight: 900 !important;
    color: var(--c-dark-blue) !important;
    text-transform: uppercase;
    letter-spacing: -1px;
}

h1 { text-shadow: 2px 2px 0px var(--c-yellow); }

.pop-card {
    background-color: white;
    border: 3px solid #000000;
    border-radius: 15px;
    padding: 20px;
    box-shadow: 5px 5px 0px 0px #000000;
    margin-bottom: 20px;
}

.pop-card-blue { background-color: var(--c-med-blue); color: white; }
.pop-card-pink { background-color: var(--c-pink); color: white; }
.pop-card-yellow { background-color: var(--c-yellow); color: black; }

.stButton > button {
    background-color: var(--c-pink);
    color: white;
    border: 3px solid black;
    border-radius: 12px;
    font-weight: 900;
    text-transform: uppercase;
    box-shadow: 4px 4px 0px 0px #000000;
    transition: all 0.1s ease;
}
.stButton > button:hover {
    transform: translate(2px, 2px);
    box-shadow: 2px 2px 0px 0px #000000;
    color: white;
    border-color: black;
}

div[data-baseweb="select"] > div {
    border: 2px solid black;
    border-radius: 10px;
    background-color: white;
}

div[data-testid="stMetricValue"] {
    font-family: 'Montserrat', sans-serif;
    font-weight: 900;
    color: var(--c-dark-blue);
    text-shadow: 2px 2px 0px var(--c-yellow);
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
            res = backend_api.analyze_suitability(
                selected_plant, st.session_state.lat, st.session_state.lon
            )
            st.session_state.analysis_result = res

            if "error" not in res:
                st.session_state.regional_scan = backend_api.scan_continent_heatmap(
                    selected_plant,
                    st.session_state.lat,
                    st.session_state.lon,
                    num_samples=150,
                )
            st.rerun()

# RESULTS
if st.session_state.analysis_result:
    res = st.session_state.analysis_result

    if "error" in res:
        st.error(res["error"])
    else:
        score = res["score"]

        # POP-CARD 1: SUITABILITY GAUGE
        st.markdown('<div class="pop-card">', unsafe_allow_html=True)
        st.plotly_chart(
            create_circular_gauge(score),
            use_container_width=True,
            config={"displayModeBar": False},
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # POP-CARD 2: RADAR + DIVERGING BAR
        st.markdown('<div class="pop-card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)

        with col1:
            st.plotly_chart(
                create_radar_chart(selected_plant, "Location", res),
                use_container_width=True,
                config={"displayModeBar": False},
            )

        with col2:
            st.plotly_chart(
                create_diverging_bar_chart(selected_plant, "Location", res),
                use_container_width=True,
                config={"displayModeBar": False},
            )

        st.markdown("</div>", unsafe_allow_html=True)

        # POP-CARD 3: MAP + TOP COUNTRIES
        if not st.session_state.regional_scan.empty:
            st.markdown('<div class="pop-card">', unsafe_allow_html=True)

            st.markdown("### BEST GROWING LOCATIONS")

            col1, col2 = st.columns([2, 1])

            with col1:
                df_scan = st.session_state.regional_scan

                # Get top countries data
                top_countries = backend_api.get_top_countries(
                    selected_plant, st.session_state.regional_scan
                )

                # Create simple choropleth map WITHOUT country labels
                m_heat = folium.Map(
                    location=[50, 10],
                    zoom_start=4,
                    tiles="OpenStreetMap",  # Simple clean map
                )

                # GeoJSON URL for European countries
                geojson_url = "https://raw.githubusercontent.com/leakyMirror/map-of-europe/master/GeoJSON/europe.geojson"

                if not df_scan.empty and "country" in df_scan.columns:
                    # Create country-score mapping
                    country_data = df_scan.set_index("country")["score"].to_dict()

                    # Color scale function
                    def get_color(score):
                        if pd.isna(score):
                            return "#e0e0e0"  # Light gray for no data
                        elif score >= 80:
                            return "#0a3d62"  # Dark blue
                        elif score >= 60:
                            return "#3c6382"  # Medium blue
                        elif score >= 40:
                            return "#60a3bc"  # Light blue
                        else:
                            return "#95afc0"  # Very light blue

                    # Add GeoJSON layer WITHOUT labels
                    folium.GeoJson(
                        geojson_url,
                        name="geojson",
                        style_function=lambda feature: {
                            "fillColor": get_color(
                                country_data.get(
                                    feature["properties"].get("NAME", ""), None
                                )
                            ),
                            "color": "#333333",  # Dark border
                            "weight": 0.5,
                            "fillOpacity": 0.8,
                        },
                    ).add_to(m_heat)

                # Add current location marker
                folium.Marker(
                    [st.session_state.lat, st.session_state.lon],
                    popup=f"Your Location",
                    icon=folium.Icon(color="red", icon="star"),
                ).add_to(m_heat)

                # Add legend
                legend_html = """
                <div style="position: fixed; bottom: 50px; left: 50px; z-index:9999; 
                            background-color:white; border:3px solid black; border-radius:10px;
                            padding:10px; box-shadow: 3px 3px 0px black;">
                    <p style="margin:0; font-weight:bold; font-size:14px;">Suitability</p>
                    <p style="margin:5px 0;"><span style="background:#0a3d62; width:20px; height:10px; display:inline-block; margin-right:5px;"></span>80-100</p>
                    <p style="margin:5px 0;"><span style="background:#3c6382; width:20px; height:10px; display:inline-block; margin-right:5px;"></span>60-80</p>
                    <p style="margin:5px 0;"><span style="background:#60a3bc; width:20px; height:10px; display:inline-block; margin-right:5px;"></span>40-60</p>
                    <p style="margin:5px 0;"><span style="background:#95afc0; width:20px; height:10px; display:inline-block; margin-right:5px;"></span>0-40</p>
                    <p style="margin:5px 0;"><span style="background:#e0e0e0; width:20px; height:10px; display:inline-block; margin-right:5px;"></span>No Data</p>
                </div>
                """
                m_heat.get_root().html.add_child(folium.Element(legend_html))

                st_folium(m_heat, height=500, use_container_width=True)

            with col2:
                st.markdown("### TOP COUNTRIES")

                if not top_countries.empty:
                    st.plotly_chart(
                        create_top_countries_chart(top_countries),
                        use_container_width=True,
                        config={"displayModeBar": False},
                    )
                else:
                    st.info("Not enough data")

            st.markdown("</div>", unsafe_allow_html=True)
