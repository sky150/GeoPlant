import plotly.graph_objects as go
import pandas as pd

# COLORS
C_PINK = "#F15CE3"
C_YELLOW = "#DAFF15"
C_LIME = "#BDD409"
C_BLACK = "#000000"
C_MED_BLUE = "#1F89D8"
C_DARK_BLUE = "#1162AC"


def _normalize(val, min_v, max_v):
    if val is None:
        return 50
    return max(0, min(100, (val - min_v) / (max_v - min_v) * 100))


def _convert_real_data_to_df(real_data):
    climate = real_data["climate"]
    plant = real_data["plant"]

    bounds = {
        "Temperature": (-10, 40),
        "Rain": (0, 3000),
        "pH": (4, 9),
        "Sun": (0, 100),
        "Hum": (0, 100),
    }

    p_temp = _normalize(
        (plant["Min_Temp"] + plant["Max_Temp"]) / 2, *bounds["Temperature"]
    )
    p_rain = _normalize((plant["Min_Rain"] + plant["Max_Rain"]) / 2, *bounds["Rain"])

    l_temp = _normalize(climate["mean_temp"], *bounds["Temperature"])
    l_rain = _normalize(climate["rain"], *bounds["Rain"])

    l_ph = _normalize(6.5, *bounds["pH"])
    l_sun = _normalize(80, *bounds["Sun"])
    l_hum = _normalize(60, *bounds["Hum"])

    data = [
        ("Temperature", p_temp, l_temp),
        ("Rainfall", p_rain, l_rain),
        ("Sunlight", 80, l_sun),
        ("pH", 50, l_ph),
        ("Humidity", 50, l_hum),
    ]

    df = pd.DataFrame(data, columns=["condition", "plant_optimum", "local_value"])
    df["difference"] = df["local_value"] - df["plant_optimum"]
    return df


def create_circular_gauge(score, height=350):
    """Circular gauge with percentage"""
    if score >= 70:
        color = "#2ECC71"
    elif score >= 40:
        color = C_YELLOW
    else:
        color = "#E74C3C"

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={
                "suffix": "%",
                "font": {"size": 50, "family": "Montserrat", "color": C_DARK_BLUE},
            },
            title={
                "text": "SUITABILITY",
                "font": {"size": 20, "family": "Montserrat", "color": C_DARK_BLUE},
            },
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 2, "tickcolor": C_BLACK},
                "bar": {"color": color, "thickness": 0.75},
                "bgcolor": "white",
                "borderwidth": 3,
                "bordercolor": C_BLACK,
                "steps": [
                    {"range": [0, 40], "color": "rgba(231, 76, 60, 0.1)"},
                    {"range": [40, 70], "color": "rgba(218, 255, 21, 0.1)"},
                    {"range": [70, 100], "color": "rgba(46, 204, 113, 0.1)"},
                ],
            },
        )
    )

    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=60, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Poppins"},
    )

    return fig


def create_radar_chart(plant_name, loc_name, real_data, height=350):
    if not real_data:
        return go.Figure()

    df = _convert_real_data_to_df(real_data)

    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=df["plant_optimum"].tolist() + [df["plant_optimum"].iloc[0]],
            theta=df["condition"].tolist() + [df["condition"].iloc[0]],
            fill="toself",
            name="Target",
            line=dict(color=C_BLACK, width=2),
            fillcolor="rgba(241, 92, 227, 0.4)",
        )
    )

    fig.add_trace(
        go.Scatterpolar(
            r=df["local_value"].tolist() + [df["local_value"].iloc[0]],
            theta=df["condition"].tolist() + [df["condition"].iloc[0]],
            fill="toself",
            name="Actual",
            line=dict(color=C_BLACK, dash="dot", width=2),
            fillcolor="rgba(31, 137, 216, 0.4)",
        )
    )

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5
        ),
        height=height,
        margin=dict(t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Poppins"},
    )
    return fig


def create_diverging_bar_chart(plant_name, loc_name, real_data, height=350):
    if not real_data:
        return go.Figure()

    df = _convert_real_data_to_df(real_data)

    colors = [C_PINK if x < 0 else C_LIME for x in df["difference"]]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=df["condition"],
            x=df["difference"],
            orientation="h",
            marker=dict(color=colors, line=dict(color=C_BLACK, width=1)),
        )
    )

    fig.update_layout(
        height=height,
        margin=dict(t=20, b=20, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Poppins"},
        xaxis=dict(
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor="rgba(0,0,0,0.5)",
            showticklabels=False,
            showgrid=False,
        ),
        yaxis=dict(tickfont=dict(size=11)),
    )
    return fig


def create_top_countries_chart(top_countries_df, height=500):
    if top_countries_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No data",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16),
        )
        return fig

    df = top_countries_df.sort_values("avg_score", ascending=True)

    colors = []
    for score in df["avg_score"]:
        if score >= 70:
            colors.append("#2ECC71")
        elif score >= 40:
            colors.append(C_YELLOW)
        else:
            colors.append("#E74C3C")

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            y=df["country"],
            x=df["avg_score"],
            orientation="h",
            marker=dict(color=colors, line=dict(color=C_BLACK, width=2)),
            text=[f"{x:.0f}" for x in df["avg_score"]],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Score: %{x:.0f}<extra></extra>",
        )
    )

    fig.update_layout(
        height=height,
        xaxis=dict(title="", range=[0, 110], showgrid=False, showticklabels=False),
        yaxis=dict(
            title="", tickfont=dict(size=12, family="Poppins", color=C_DARK_BLUE)
        ),
        margin=dict(l=10, r=30, t=10, b=10),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Poppins"},
    )

    return fig
