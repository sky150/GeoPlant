import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import backend_api  # This imports your logic file

# ---------------------------------------------------------
# UI CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(page_title="GeoPlant Analytics", layout="wide", page_icon="🌱")

COLOR_IDEAL = "#2ECC71"  # Green
COLOR_RISK = "#E74C3C"   # Red
COLOR_WARN = "#F1C40F"   # Orange

# Initialize Session State for Coordinates (So they survive reloads)
if 'lat' not in st.session_state: st.session_state.lat = 47.3769 # Default: Zurich
if 'lon' not in st.session_state: st.session_state.lon = 8.5417

# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------
st.title("🌍 GeoPlant: Smart Crop Suitability Engine")
st.markdown("Precision agriculture tool powered by **PostGIS** and **CHELSA Climate Data**.")

# ---------------------------------------------------------
# STEP 1: SELECT PLANT
# ---------------------------------------------------------
with st.container():
    st.markdown("### 1️⃣ Select Crop")
    
    # Fetch plant list from the Database via Backend API
    try:
        plant_list = backend_api.get_plant_list()
    except Exception:
        plant_list = []

    if not plant_list:
        st.error("🚨 Database Error: Could not fetch plants. Run `clean_and_upload.py` first.")
        st.stop()
        
    selected_plant = st.selectbox("I want to grow:", plant_list)

# ---------------------------------------------------------
# STEP 2: SELECT LOCATION (Interactive Map)
# ---------------------------------------------------------
st.divider()
st.markdown("### 2️⃣ Select Location")

col_map, col_controls = st.columns([2, 1])

with col_map:
    # Create the base map
    m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=5)
    
    # Add a marker for the current selection
    folium.Marker(
        [st.session_state.lat, st.session_state.lon], 
        popup="Selected Target", 
        tooltip="Click anywhere to move me",
        icon=folium.Icon(color="green", icon="leaf")
    ).add_to(m)
    
    # Render the map and capture clicks
    st.caption("👇 Click anywhere on the map to update coordinates.")
    map_output = st_folium(m, height=400, use_container_width=True)

    # LOGIC: If map was clicked, update the session state variables
    if map_output['last_clicked']:
        new_lat = map_output['last_clicked']['lat']
        new_lng = map_output['last_clicked']['lng']
        
        # Only rerun if the click is actually new (prevents infinite loops)
        if round(new_lat, 4) != round(st.session_state.lat, 4):
            st.session_state.lat = new_lat
            st.session_state.lon = new_lng
            st.rerun()

with col_controls:
    st.markdown("**Coordinates**")
    
    # These inputs are linked to session_state
    lat_input = st.number_input("Latitude", value=st.session_state.lat, format="%.4f", key="input_lat")
    lon_input = st.number_input("Longitude", value=st.session_state.lon, format="%.4f", key="input_lon")
    
    # Sync manual number input changes back to session state
    if lat_input != st.session_state.lat:
        st.session_state.lat = lat_input
        st.rerun()
    if lon_input != st.session_state.lon:
        st.session_state.lon = lon_input
        st.rerun()

    st.markdown("---")
    run_btn = st.button("🚀 Analyze Suitability", type="primary", use_container_width=True)

# ---------------------------------------------------------
# STEP 3: RESULTS ENGINE
# ---------------------------------------------------------
if run_btn:
    st.divider()
    
    # Call the Backend API (The "Black Box")
    with st.spinner(f"Querying 50GB Climate Database for {selected_plant}..."):
        result = backend_api.analyze_suitability(selected_plant, st.session_state.lat, st.session_state.lon)

    # Error Handling
    if "error" in result:
        st.error(f"❌ Analysis Failed: {result['error']}")
    else:
        # Unpack Results
        score = result['score']
        status = result['status']
        climate = result['climate']
        plant = result['plant']
        reasons = result['reasons']

        # --- TOP SECTION: SCORE & STATUS ---
        c1, c2 = st.columns([1, 2])
        
        with c1:
            # Gauge Chart
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = score,
                title = {'text': "Suitability Score"},
                gauge = {
                    'axis': {'range': [0, 100]},
                    'bar': {'color': COLOR_IDEAL if score > 80 else (COLOR_WARN if score > 40 else COLOR_RISK)},
                    'steps': [{'range': [0, 100], 'color': "whitesmoke"}]
                }
            ))
            fig_gauge.update_layout(height=250, margin=dict(t=30, b=20, l=20, r=20))
            st.plotly_chart(fig_gauge, use_container_width=True)

        with c2:
            st.subheader(f"Status: {status}")
            
            # Display Issues or Success Message
            if reasons:
                for issue in reasons:
                    if "CRITICAL" in issue:
                        st.error(issue)
                    else:
                        st.warning(issue)
            else:
                st.success(f"✅ Perfect Match! {selected_plant} will thrive here.")

            # Display Real Data Summary
            st.info(f"""
            **Local Climate Data (From Database):**
            ❄️ Winter Low: **{climate['min_temp']}°C** (Plant needs > {plant['Min_Temp']}°C)
            ☀️ Summer High: **{climate['max_temp']}°C**
            💧 Annual Rain: **{climate['rain']}mm** (Plant needs {plant['Min_Rain']}mm)
            """)

        # --- BOTTOM SECTION: VISUAL DIAGNOSTICS ---
        st.subheader("🔬 Diagnostic Charts")
        tab1, tab2 = st.tabs(["Radar Analysis", "Seasonal Projection"])

        with tab1:
            # --- RADAR CHART LOGIC ---
            # Helper to normalize values to 0-1 for the chart
            def norm(val, min_v, max_v):
                return (val - min_v) / (max_v - min_v) if max_v != min_v else 0.5
            
            categories = ['Temp', 'Rain', 'pH', 'Humidity', 'Sun', 'Elevation']
            
            # Global Bounds (The "World" Limits)
            bounds = {
                'Temp': (-10, 40), 'Rain': (0, 3000), 'pH': (4, 9),
                'Hum': (20, 100), 'Sun': (0, 100), 'Elev': (0, 3000)
            }

            # Prepare Data for Chart
            # 1. Plant Limits (Green Zone)
            p_min = [
                norm(plant['Min_Temp'], *bounds['Temp']), norm(plant['Min_Rain'], *bounds['Rain']),
                norm(plant['Min_pH'], *bounds['pH']), norm(plant['Ideal_Hum']-20, *bounds['Hum']),
                norm(plant['Sun_Need']-20, *bounds['Sun']), 0
            ]
            p_max = [
                norm(plant['Max_Temp'], *bounds['Temp']), norm(plant['Max_Rain'], *bounds['Rain']),
                norm(plant['Max_pH'], *bounds['pH']), norm(plant['Ideal_Hum']+20, *bounds['Hum']),
                norm(plant['Sun_Need']+20, *bounds['Sun']), norm(plant['Max_Elev'], *bounds['Elev'])
            ]
            
            # 2. Actual Location Data (Blue Line)
            loc_val = [
                norm(climate['mean_temp'], *bounds['Temp']), norm(climate['rain'], *bounds['Rain']),
                norm(climate['ph'], *bounds['pH']), norm(climate['humidity'], *bounds['Hum']),
                norm(climate['sun'], *bounds['Sun']), norm(climate['elevation'], *bounds['Elev'])
            ]
            
            # Close the polygon loop (connect end to start)
            p_min += [p_min[0]]; p_max += [p_max[0]]; loc_val += [loc_val[0]]
            cats = categories + [categories[0]]

            # Plot
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(r=p_max, theta=cats, fill='toself', fillcolor='rgba(46, 204, 113, 0.2)', line=dict(color='green'), name='Safe Zone (Max)'))
            fig_radar.add_trace(go.Scatterpolar(r=p_min, theta=cats, fill='toself', fillcolor='white', line=dict(color='green', dash='dot'), name='Safe Zone (Min)'))
            fig_radar.add_trace(go.Scatterpolar(r=loc_val, theta=cats, line=dict(color='blue', width=3), name='Actual Location'))
            
            fig_radar.update_layout(polar=dict(radialaxis=dict(visible=False, range=[0, 1])), showlegend=True, height=450)
            st.plotly_chart(fig_radar, use_container_width=True)
            st.caption("*Note: pH, Sun, and Humidity are currently simulated/mocked values.")

        with tab2:
            # --- SEASONALITY CHART LOGIC ---
            months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            
            # Simulate a Sine Wave for the year using the Real Min/Max from DB
            # We assume coldest is Jan, hottest is July
            amp = (climate['max_temp'] - climate['min_temp']) / 2
            mean = (climate['max_temp'] + climate['min_temp']) / 2
            
            # Use negative Cosine to put the valley in Jan and peak in July
            sim_temps = [mean + amp * -np.cos(i * 2 * np.pi / 12) for i in range(12)]
            
            fig_line = go.Figure()
            
            # Draw Green Safe Band
            fig_line.add_hrect(y0=plant['Min_Temp'], y1=plant['Max_Temp'], fillcolor="green", opacity=0.15, line_width=0, annotation_text="Safe Temperature Zone")
            
            # Draw Temperature Curve
            fig_line.add_trace(go.Scatter(x=months, y=sim_temps, mode='lines+markers', line=dict(color='blue', width=4), name="Projected Temp"))
            
            # Draw Freezing Line
            fig_line.add_hline(y=0, line_dash="dash", line_color="navy", annotation_text="Freezing (0°C)")

            fig_line.update_layout(title="Annual Temperature Cycle vs Plant Limits", yaxis_title="Temperature (°C)", height=450)
            st.plotly_chart(fig_line, use_container_width=True)
