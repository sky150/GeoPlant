import psycopg2
import os
import numpy as np
import pandas as pd


def get_db_connection():
    try:
        return psycopg2.connect(
            host=os.getenv("DB_HOST", "geoplant_db"),
            database=os.getenv("DB_NAME", "geoplant"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASS", "admin"),
        )
    except Exception as e:
        print(f"DB Error: {e}")
        return None


def get_real_climate(lat, lon):
    conn = get_db_connection()
    if not conn:
        return None

    lat = float(lat)
    lon = float(lon)

    query = """
    SELECT 
        ST_Value(mean.rast, ST_SetSRID(ST_Point(%s, %s), 4326)) as raw_mean,
        ST_Value(min.rast, ST_SetSRID(ST_Point(%s, %s), 4326)) as raw_min,
        ST_Value(max.rast, ST_SetSRID(ST_Point(%s, %s), 4326)) as raw_max,
        ST_Value(rain.rast, ST_SetSRID(ST_Point(%s, %s), 4326)) as raw_rain,
        ST_Value(dry.rast, ST_SetSRID(ST_Point(%s, %s), 4326)) as raw_dry,
        ST_Value(seas.rast, ST_SetSRID(ST_Point(%s, %s), 4326)) as raw_season
    FROM 
        climate_temp_mean mean, climate_temp_min min, climate_temp_max max,
        climate_rain rain, climate_rain_driest dry, climate_rain_seasonality seas
    WHERE 
        ST_Intersects(mean.rast, ST_SetSRID(ST_Point(%s, %s), 4326)) AND
        ST_Intersects(min.rast, ST_SetSRID(ST_Point(%s, %s), 4326)) AND
        ST_Intersects(max.rast, ST_SetSRID(ST_Point(%s, %s), 4326)) AND
        ST_Intersects(rain.rast, ST_SetSRID(ST_Point(%s, %s), 4326)) AND
        ST_Intersects(dry.rast, ST_SetSRID(ST_Point(%s, %s), 4326)) AND
        ST_Intersects(seas.rast, ST_SetSRID(ST_Point(%s, %s), 4326));
    """

    cur = conn.cursor()
    args = (lon, lat) * 12
    try:
        cur.execute(query, args)
        result = cur.fetchone()
        conn.close()

        if not result or result[0] is None:
            return None

        def c_temp(val):
            if val is None:
                return 0
            if val > 1000:
                return (val / 10.0) - 273.15
            return val / 10.0

        def c_rain(val):
            if val is None:
                return 0
            return val / 10.0 if val > 5000 else val

        return {
            "mean_temp": round(c_temp(result[0]), 1),
            "min_temp": round(c_temp(result[1]), 1),
            "max_temp": round(c_temp(result[2]), 1),
            "rain": int(c_rain(result[3])),
            "driest_month_rain": int(c_rain(result[4])),
            "seasonality": int(result[5]) if result[5] else 0,
            "ph": 6.5,
            "humidity": 60,
            "sun": 80,
            "elevation": 500,
        }
    except Exception as e:
        print(f"SQL Execution Error: {e}")
        return None


def get_plant_list():
    conn = get_db_connection()
    if not conn:
        return []
    cur = conn.cursor()
    cur.execute("SELECT name FROM plants ORDER BY name ASC")
    res = [r[0] for r in cur.fetchall()]
    conn.close()
    return res


def get_plant_rules(plant_name):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT min_temp_c, max_temp_c, min_rain_mm, max_rain_mm, min_ph, max_ph FROM plants WHERE name = %s",
        (plant_name,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "name": plant_name,
        "Min_Temp": row[0],
        "Max_Temp": row[1],
        "Min_Rain": row[2],
        "Max_Rain": row[3],
        "Min_pH": row[4],
        "Max_pH": row[5],
        "Ideal_Hum": 50,
        "Sun_Need": 80,
        "Max_Elev": 2000,
    }


def analyze_suitability(plant_name, lat, lon):
    climate = get_real_climate(lat, lon)
    plant = get_plant_rules(plant_name)

    if not climate:
        return {"error": "Ocean/No Data"}
    if not plant:
        return {"error": "Plant Missing"}

    score = 100
    reasons = []
    status = "Ideal"

    if climate["min_temp"] < plant["Min_Temp"]:
        deficit = plant["Min_Temp"] - climate["min_temp"]
        score = max(0, score - (deficit * 10))
        if score < 20:
            status = "Dead"
        else:
            status = "Risk"

    if climate["rain"] < plant["Min_Rain"]:
        deficit = plant["Min_Rain"] - climate["rain"]
        penalty = min(40, (deficit / plant["Min_Rain"]) * 40)
        score -= penalty
        status = "Risk" if score > 50 else "Poor"

    if climate["max_temp"] > plant["Max_Temp"]:
        excess = climate["max_temp"] - plant["Max_Temp"]
        penalty = min(30, excess * 3)
        score -= penalty
        if status not in ["Dead", "Risk"]:
            status = "Stress"

    if climate["rain"] > plant["Max_Rain"]:
        excess = climate["rain"] - plant["Max_Rain"]
        penalty = min(20, (excess / plant["Max_Rain"]) * 20)
        score -= penalty

    return {
        "score": max(0, min(100, score)),
        "status": status,
        "reasons": reasons,
        "climate": climate,
        "plant": plant,
    }


def scan_continent_heatmap(plant_name, center_lat, center_lon, num_samples=200):
    """
    Scans continent strategically - focuses on country centers for speed
    Returns country-level aggregated data
    """
    results = []
    bounds = get_continent_bounds(center_lat, center_lon)

    # Strategic sampling: focus on known country centers in the continent
    country_centers = {
        "Spain": (40.4, -3.7),
        "France": (46.6, 2.3),
        "Germany": (51.2, 10.4),
        "Italy": (41.9, 12.6),
        "United Kingdom": (54.0, -2.5),
        "Greece": (39.1, 21.8),
        "Turkey": (39.0, 35.0),
        "Norway": (60.5, 8.5),
        "Sweden": (62.0, 15.0),
        "Finland": (64.0, 26.0),
        "Poland": (52.0, 19.0),
        "Portugal": (39.5, -8.0),
        "Netherlands": (52.3, 5.5),
        "Belgium": (50.8, 4.3),
        "Switzerland": (46.8, 8.2),
        "Austria": (47.5, 14.5),
        "Czech Republic": (49.8, 15.5),
        "Hungary": (47.2, 19.5),
        "Romania": (46.0, 25.0),
        "Bulgaria": (42.7, 25.5),
        "Croatia": (45.8, 16.0),
        "Serbia": (44.0, 21.0),
        "Ukraine": (49.0, 32.0),
        "Belarus": (53.9, 27.6),
        "Denmark": (56.0, 10.0),
        "Ireland": (53.0, -8.0),
        "Iceland": (65.0, -18.0),
        "Albania": (41.0, 20.0),
        "North Macedonia": (41.6, 21.7),
        "Bosnia": (44.0, 18.0),
        "Slovakia": (48.7, 19.5),
        "Slovenia": (46.1, 14.8),
        "Estonia": (59.0, 26.0),
        "Latvia": (57.0, 25.0),
        "Lithuania": (55.0, 24.0),
        "Moldova": (47.0, 29.0),
        "Montenegro": (42.5, 19.3),
        "Kosovo": (42.6, 20.9),
    }

    # Sample around each country center
    for country, (lat, lon) in country_centers.items():
        # Check if country is in our bounds
        if (
            bounds["lat_min"] <= lat <= bounds["lat_max"]
            and bounds["lon_min"] <= lon <= bounds["lon_max"]
        ):

            # Sample 5 points around each country center
            offsets = [
                (0, 0),  # center
                (1, 0),
                (-1, 0),  # north/south
                (0, 1),
                (0, -1),  # east/west
            ]

            country_scores = []
            for dlat, dlon in offsets:
                test_lat = lat + dlat
                test_lon = lon + dlon

                res = analyze_suitability(plant_name, test_lat, test_lon)
                if "error" not in res:
                    country_scores.append(res["score"])

            # Average score for this country
            if country_scores:
                avg_score = sum(country_scores) / len(country_scores)
                results.append(
                    {"country": country, "lat": lat, "lon": lon, "score": avg_score}
                )

    if not results:
        return pd.DataFrame(columns=["country", "lat", "lon", "score"])

    return pd.DataFrame(results)


def get_continent_bounds(lat, lon):
    """Returns approximate bounds for the continent"""
    # Europe
    if 35 <= lat <= 70 and -10 <= lon <= 40:
        return {
            "lat_min": 35,
            "lat_max": 70,
            "lon_min": -10,
            "lon_max": 40,
            "name": "Europe",
        }
    # North America
    elif 15 <= lat <= 70 and -170 <= lon <= -50:
        return {
            "lat_min": 15,
            "lat_max": 70,
            "lon_min": -170,
            "lon_max": -50,
            "name": "North America",
        }
    # South America
    elif -55 <= lat <= 15 and -85 <= lon <= -35:
        return {
            "lat_min": -55,
            "lat_max": 15,
            "lon_min": -85,
            "lon_max": -35,
            "name": "South America",
        }
    # Africa
    elif -35 <= lat <= 37 and -20 <= lon <= 52:
        return {
            "lat_min": -35,
            "lat_max": 37,
            "lon_min": -20,
            "lon_max": 52,
            "name": "Africa",
        }
    # Asia
    elif 5 <= lat <= 70 and 40 <= lon <= 150:
        return {
            "lat_min": 5,
            "lat_max": 70,
            "lon_min": 40,
            "lon_max": 150,
            "name": "Asia",
        }
    # Oceania
    elif -50 <= lat <= 0 and 110 <= lon <= 180:
        return {
            "lat_min": -50,
            "lat_max": 0,
            "lon_min": 110,
            "lon_max": 180,
            "name": "Oceania",
        }

    return {
        "lat_min": lat - 10,
        "lat_max": lat + 10,
        "lon_min": lon - 10,
        "lon_max": lon + 10,
        "name": "Region",
    }


def get_top_countries(plant_name, scan_df):
    """
    Estimates top countries from scan data
    Returns empty DataFrame if not enough data
    """
    if scan_df.empty or len(scan_df) < 10:
        return pd.DataFrame(columns=["country", "avg_score"])

    def estimate_country(lat, lon):
        if 40 <= lat <= 44 and -9 <= lon <= 3:
            return "Spain"
        elif 41 <= lat <= 51 and -5 <= lon <= 10:
            return "France"
        elif 45 <= lat <= 55 and 5 <= lon <= 15:
            return "Germany"
        elif 36 <= lat <= 47 and 6 <= lon <= 19:
            return "Italy"
        elif 49 <= lat <= 60 and -8 <= lon <= 2:
            return "United Kingdom"
        elif 36 <= lat <= 43 and 19 <= lon <= 29:
            return "Greece"
        elif 38 <= lat <= 42 and 26 <= lon <= 45:
            return "Turkey"
        elif 55 <= lat <= 70 and 10 <= lon <= 31:
            return "Scandinavia"
        elif 45 <= lat <= 56 and 14 <= lon <= 24:
            return "Poland"
        elif 41 <= lat <= 52 and -10 <= lon <= -6:
            return "Portugal"
        elif 56 <= lat <= 70 and 20 <= lon <= 35:
            return "Baltic States"
        elif 43 <= lat <= 50 and 20 <= lon <= 30:
            return "Balkans"
        else:
            return "Other"

    scan_df["country"] = scan_df.apply(
        lambda row: estimate_country(row["lat"], row["lon"]), axis=1
    )

    country_scores = (
        scan_df.groupby("country")["score"].agg(["mean", "count"]).reset_index()
    )
    country_scores.columns = ["country", "avg_score", "count"]

    # Filter: must have at least 2 samples and not be "Other"
    country_scores = country_scores[
        (country_scores["country"] != "Other") & (country_scores["count"] >= 2)
    ]

    # Sort and get top 10
    if len(country_scores) == 0:
        return pd.DataFrame(columns=["country", "avg_score"])

    top_countries = country_scores.nlargest(min(10, len(country_scores)), "avg_score")[
        ["country", "avg_score"]
    ]

    return top_countries


def get_top_countries(plant_name, scan_df):
    """
    Estimates top countries from scan data
    Groups by approximate country regions and returns top performers
    """
    if scan_df.empty:
        return pd.DataFrame(columns=["country", "avg_score"])

    # Simple country mapping based on lat/lon (Europe focused)
    def estimate_country(lat, lon):
        # This is a simplified version - you could use a proper geocoding API
        if 40 <= lat <= 44 and -9 <= lon <= 3:
            return "Spain"
        elif 41 <= lat <= 51 and -5 <= lon <= 10:
            return "France"
        elif 45 <= lat <= 55 and 5 <= lon <= 15:
            return "Germany"
        elif 36 <= lat <= 47 and 6 <= lon <= 19:
            return "Italy"
        elif 49 <= lat <= 60 and -8 <= lon <= 2:
            return "United Kingdom"
        elif 36 <= lat <= 43 and 19 <= lon <= 29:
            return "Greece"
        elif 38 <= lat <= 42 and 26 <= lon <= 45:
            return "Turkey"
        elif 55 <= lat <= 70 and 10 <= lon <= 31:
            return "Scandinavia"
        elif 45 <= lat <= 56 and 14 <= lon <= 24:
            return "Poland"
        elif 41 <= lat <= 52 and -10 <= lon <= -6:
            return "Portugal"
        else:
            return "Other"

    scan_df["country"] = scan_df.apply(
        lambda row: estimate_country(row["lat"], row["lon"]), axis=1
    )

    # Group by country and get average score
    country_scores = (
        scan_df.groupby("country")["score"].agg(["mean", "count"]).reset_index()
    )
    country_scores.columns = ["country", "avg_score", "count"]

    # Filter out "Other" and countries with too few samples
    country_scores = country_scores[
        (country_scores["country"] != "Other") & (country_scores["count"] >= 3)
    ]

    # Sort by score and get top 10
    top_countries = country_scores.nlargest(10, "avg_score")[["country", "avg_score"]]

    return top_countries
