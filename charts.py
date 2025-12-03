import plotly.graph_objects as go
import plotly.express as px
from charts_example_data import (
    plants,
    CONDITIONS,
    get_plant_location_profile,
    compute_location_scores_for_plant,
    location_climate
)

def create_radar_chart(plant: str, location: str):
    """Erstellt Radar-Chart: Pflanze vs. Örtliche Bedingungen"""
    df = get_plant_location_profile(plant, location)

    fig = go.Figure()

    # Pflanze perfekte Bedingungen (Farbe 1)
    fig.add_trace(go.Scatterpolar(
        r=df["plant_optimum"].tolist() + [df["plant_optimum"].iloc[0]],
        theta=df["condition"].tolist() + [df["condition"].iloc[0]],
        fill='toself',
        name=f'{plant} (Ideal)',
        line=dict(color='#10b981', width=2),
        fillcolor='rgba(16, 185, 129, 0.3)'
    ))

    # Örtliche Bedingungen (Farbe 2)
    fig.add_trace(go.Scatterpolar(
        r=df["local_value"].tolist() + [df["local_value"].iloc[0]],
        theta=df["condition"].tolist() + [df["condition"].iloc[0]],
        fill='toself',
        name=f'{location} (Aktuell)',
        line=dict(color='#3b82f6', width=2),
        fillcolor='rgba(59, 130, 246, 0.3)'
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(size=11)
            )
        ),
        showlegend=True,
        title=dict(
            text=f"Wachstumsbedingungen: {plant} in {location}",
            font=dict(size=18, family="Arial, sans-serif"),
            x=0.5,
            xanchor='center'
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5
        ),
        height=500
    )

    return fig


def create_diverging_bar_chart(plant: str, location: str):
    """Erstellt horizontales Diverging Bar Chart: Abweichung vom Ideal"""
    df = get_plant_location_profile(plant, location)

    # Farben basierend auf positiver/negativer Abweichung
    colors = ['#ef4444' if x < 0 else '#10b981' for x in df["difference"]]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df["condition"],
        x=df["difference"],
        orientation='h',
        marker=dict(
            color=colors,
            line=dict(color='rgba(0,0,0,0.3)', width=1)
        ),
        text=[f"{val:+.0f}" for val in df["difference"]],
        textposition='outside',
        hovertemplate='<b>%{y}</b><br>Abweichung: %{x:+.1f}<br><extra></extra>'
    ))

    fig.update_layout(
        title=dict(
            text=f"Abweichung vom Ideal: {plant} in {location}",
            font=dict(size=18, family="Arial, sans-serif"),
            x=0.5,
            xanchor='center'
        ),
        xaxis=dict(
            title="Abweichung vom Ideal",
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor='rgba(0,0,0,0.5)',
            tickfont=dict(size=11),
            title_font=dict(size=13)
        ),
        yaxis=dict(
            title="",
            tickfont=dict(size=12)
        ),
        height=400,
        showlegend=False,
        annotations=[
            dict(
                x=-50,
                y=1.12,
                xref='x',
                yref='paper',
                text='← Zu wenig',
                showarrow=False,
                font=dict(size=12, color='#ef4444')
            ),
            dict(
                x=50,
                y=1.12,
                xref='x',
                yref='paper',
                text='Zu viel →',
                showarrow=False,
                font=dict(size=12, color='#10b981')
            )
        ]
    )

    return fig


def create_bubble_map(plant: str):
    """Erstellt Bubble Map: Perfekte Wachstumsbedingungen weltweit"""
    scores = compute_location_scores_for_plant(plant)

    fig = go.Figure()

    fig.add_trace(go.Scattergeo(
        lon=scores["lon"],
        lat=scores["lat"],
        text=scores["location"],
        mode='markers+text',
        marker=dict(
            size=scores["growth_score"] * 0.5,  # Skalierung für Bubble-Größe
            color=scores["growth_score"],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(
                title="Growth<br>Score",
                tickfont=dict(size=11),
                title_font=dict(size=12)
            ),
            line=dict(width=1, color='rgba(255,255,255,0.8)'),
            sizemode='diameter'
        ),
        textposition="top center",
        textfont=dict(size=11, color='black'),
        hovertemplate='<b>%{text}</b><br>Growth Score: %{marker.color:.1f}<br><extra></extra>'
    ))

    fig.update_layout(
        title=dict(
            text=f"Ideale Wachstumsstandorte für {plant}",
            font=dict(size=18, family="Arial, sans-serif"),
            x=0.5,
            xanchor='center'
        ),
        geo=dict(
            projection_type='natural earth',
            showland=True,
            landcolor='rgb(243, 243, 243)',
            coastlinecolor='rgb(204, 204, 204)',
            showocean=True,
            oceancolor='rgb(230, 245, 255)',
            showcountries=True,
            countrycolor='rgb(204, 204, 204)'
        ),
        height=500,
        margin=dict(l=0, r=0, t=60, b=0)
    )

    return fig


# # Hauptprogramm zum Testen
# if __name__ == "__main__":
#     # Test-Parameter
#     selected_plant = "Tomato"
#     selected_location = "Valencia"

#     print(f"📊 Erstelle Charts für {selected_plant} in {selected_location}...\n")

#     # Chart 1: Radar Chart
#     print("1️⃣ Radar Chart wird erstellt...")
#     radar_fig = create_radar_chart(selected_plant, selected_location)
#     radar_fig.show()

#     # Chart 2: Diverging Bar Chart
#     print("2️⃣ Diverging Bar Chart wird erstellt...")
#     diverging_fig = create_diverging_bar_chart(selected_plant, selected_location)
#     diverging_fig.show()

#     # Chart 3: Bubble Map
#     print("3️⃣ Bubble Map wird erstellt...")
#     bubble_fig = create_bubble_map(selected_plant)
#     bubble_fig.show()

#     print("\n✅ Alle Charts wurden erfolgreich erstellt!")
#     print("\nTipp: Ändere 'selected_plant' und 'selected_location' um andere Kombinationen zu testen:")
#     print(f"Verfügbare Pflanzen: {plants}")
#     print(f"Verfügbare Orte: {location_climate['location'].unique().tolist()}")

# Am Ende von charts.py ersetze den __main__ Teil mit:
if __name__ == "__main__":
    from plotly.subplots import make_subplots

    selected_plant = "Tomato"
    selected_location = "Valencia"

    print(f"📊 Erstelle Charts für {selected_plant} in {selected_location}...\n")

    # Charts erstellen
    radar_fig = create_radar_chart(selected_plant, selected_location)
    diverging_fig = create_diverging_bar_chart(selected_plant, selected_location)
    bubble_fig = create_bubble_map(selected_plant)

    # Alle in einem HTML speichern und öffnen
    from plotly.offline import plot

    with open("all_charts.html", "w", encoding="utf-8") as f:
        f.write("<html><head><title>Plant Charts</title></head><body>")
        f.write(radar_fig.to_html(full_html=False, include_plotlyjs='cdn'))
        f.write("<br><br>")
        f.write(diverging_fig.to_html(full_html=False, include_plotlyjs=False))
        f.write("<br><br>")
        f.write(bubble_fig.to_html(full_html=False, include_plotlyjs=False))
        f.write("</body></html>")

    import webbrowser
    webbrowser.open("all_charts.html")

    print("\n✅ Alle Charts wurden in 'all_charts.html' gespeichert!")
