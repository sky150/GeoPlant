import plotly.graph_objects as go
import pandas as pd

# COLORS
C_PINK = "#F15CE3"
C_YELLOW = "#DAFF15"
C_LIME = "#BDD409"
C_BLACK = "#000000"
C_MED_BLUE = "#1F89D8"

def _normalize(val, min_v, max_v):
    if val is None: return 50
    return max(0, min(100, (val - min_v) / (max_v - min_v) * 100))

def _convert_real_data_to_df(real_data):
    # Extracts Real Database values into a normalized DataFrame for charts
    climate = real_data['climate']
    plant = real_data['plant']

    bounds = {
        "Temperature": (-10, 40), "Rain": (0, 3000),
        "pH": (4, 9), "Sun": (0, 100), "Hum": (0, 100)
    }

    # Normalize Plant Needs
    p_temp = _normalize((plant['Min_Temp'] + plant['Max_Temp'])/2, *bounds['Temperature'])
    p_rain = _normalize((plant['Min_Rain'] + plant['Max_Rain'])/2, *bounds['Rain'])
    
    # Normalize Real Location
    l_temp = _normalize(climate['mean_temp'], *bounds['Temperature'])
    l_rain = _normalize(climate['rain'], *bounds['Rain'])
    
    # Mocks for missing layers
    l_ph = _normalize(6.5, *bounds['pH'])
    l_sun = _normalize(80, *bounds['Sun'])
    l_hum = _normalize(60, *bounds['Hum'])

    data = [
        ("Temperature", p_temp, l_temp),
        ("Rainfall", p_rain, l_rain),
        ("Sunlight", 80, l_sun),
        ("pH", 50, l_ph),
        ("Humidity", 50, l_hum)
    ]
    
    df = pd.DataFrame(data, columns=["condition", "plant_optimum", "local_value"])
    df["difference"] = df["local_value"] - df["plant_optimum"]
    return df

def create_radar_chart(plant_name, loc_name, real_data, height=500):
    if not real_data: return go.Figure()
    
    df = _convert_real_data_to_df(real_data)
    
    fig = go.Figure()
    # Ideal
    fig.add_trace(go.Scatterpolar(
        r=df["plant_optimum"].tolist() + [df["plant_optimum"].iloc[0]],
        theta=df["condition"].tolist() + [df["condition"].iloc[0]],
        fill='toself', name='Target', line=dict(color=C_BLACK),
        fillcolor='rgba(241, 92, 227, 0.4)'
    ))
    # Actual
    fig.add_trace(go.Scatterpolar(
        r=df["local_value"].tolist() + [df["local_value"].iloc[0]],
        theta=df["condition"].tolist() + [df["condition"].iloc[0]],
        fill='toself', name='Actual', line=dict(color=C_BLACK, dash='dot'),
        fillcolor='rgba(31, 137, 216, 0.4)'
    ))
    
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True, height=height, margin=dict(t=20, b=20)
    )
    return fig

def create_diverging_bar_chart(plant_name, loc_name, real_data, height=400):
    if not real_data: return go.Figure()
    df = _convert_real_data_to_df(real_data)
    
    colors = [C_PINK if x < 0 else C_LIME for x in df["difference"]]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df["condition"], x=df["difference"], orientation='h',
        marker=dict(color=colors, line=dict(color=C_BLACK, width=1))
    ))
    fig.update_layout(height=height, title="Deviation from Target", margin=dict(t=30, b=20))
    return fig

def create_bubble_map(scan_data, height=500):
    # Accepts the list of dicts from backend_api.scan_region
    if not scan_data: return go.Figure()
    
    lats = [x['lat'] for x in scan_data]
    lons = [x['lon'] for x in scan_data]
    scores = [x['score'] for x in scan_data]
    texts = [f"Score: {x['score']}" for x in scan_data]

    fig = go.Figure()
    fig.add_trace(go.Scattergeo(
        lon=lons, lat=lats, text=texts, mode='markers',
        marker=dict(
            size=[s/2 for s in scores], # Size based on score
            color=scores,
            colorscale=[[0, C_PINK], [0.5, C_YELLOW], [1, C_LIME]],
            line=dict(color=C_BLACK, width=1)
        )
    ))
    
    # Focus map on the data
    fig.update_layout(
        geo=dict(
            projection_type='natural earth',
            fitbounds="locations", # Zoom to data
            showland=True, landcolor='#f0f2f6',
            showocean=True, oceancolor=C_MED_BLUE
        ),
        height=height, margin=dict(l=0,r=0,t=0,b=0)
    )
    return fig
