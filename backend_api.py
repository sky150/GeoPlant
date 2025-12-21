import psycopg2
import os
import numpy as np
import pandas as pd
from countries import WORLD_LOCATIONS  # Import the big list
from geopy.geocoders import Nominatim


# =========================================================
# 1. DATABASE CONNECTION
# =========================================================
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


# =========================================================
# 2. LOGIC (Pure Python)
# =========================================================
def calculate_score_logic(plant, climate):
    if not climate or not plant:
        return 0, "Error", []

    score = 100
    reasons = []
    status = "Ideal"

    # Winter Kill
    if climate["min_temp"] < plant["Min_Temp"]:
        score = 0
        status = "Dead"
        reasons.append(f"❄️ Freeze: {climate['min_temp']:.1f}°C")
    # Drought
    elif climate["rain"] < plant["Min_Rain"]:
        score -= 40
        status = "Risk"
        reasons.append(f"🌵 Dry: {climate['rain']}mm")
    # Heat
    elif climate["max_temp"] > plant["Max_Temp"]:
        score -= 20
        status = "Stress"
        reasons.append(f"🔥 Hot: {climate['max_temp']:.1f}°C")
    # Wet
    elif climate["rain"] > plant["Max_Rain"]:
        score -= 10
        reasons.append(f"💧 Wet: {climate['rain']}mm")

    return max(0, int(score)), status, reasons


# =========================================================
# 3. DATA FETCHING
# =========================================================
def fetch_climate_data(cursor, lat, lon):
    lat, lon = float(lat), float(lon)

    # Efficient 6-table join for one point
    query = """
    SELECT 
        ST_Value(mean.rast, ST_SetSRID(ST_Point(%s, %s), 4326)),
        ST_Value(min.rast, ST_SetSRID(ST_Point(%s, %s), 4326)),
        ST_Value(max.rast, ST_SetSRID(ST_Point(%s, %s), 4326)),
        ST_Value(rain.rast, ST_SetSRID(ST_Point(%s, %s), 4326)),
        ST_Value(dry.rast, ST_SetSRID(ST_Point(%s, %s), 4326)),
        ST_Value(seas.rast, ST_SetSRID(ST_Point(%s, %s), 4326))
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

    try:
        cursor.execute(query, (lon, lat) * 12)
        row = cursor.fetchone()
        if not row or row[0] is None:
            return None

        # Helper to safely convert scale
        def val(idx, scale=10.0, offset=0):
            v = row[idx]
            if v is None:
                return 0
            if scale == 10.0 and v > 1000:
                return (v / 10.0) - 273.15  # Kelvin fix
            return (v / scale) + offset

        return {
            "mean_temp": round(val(0), 1),
            "min_temp": round(val(1), 1),
            "max_temp": round(val(2), 1),
            "rain": int(val(3, scale=1.0 if row[3] < 5000 else 10.0)),
            "driest_month_rain": int(val(4, scale=1.0 if row[4] < 5000 else 10.0)),
            "seasonality": int(row[5] if row[5] else 0),
            "ph": 6.5,
            "humidity": 60,
            "sun": 80,
            "elevation": 500,
        }
    except:
        return None


# =========================================================
# 4. PLANT DATA
# =========================================================
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


def get_location_name(lat, lon):
    """Returns 'Country' based on lat/lon using Geopy"""
    try:
        # Nominatim is the free OpenStreetMap geocoder
        geolocator = Nominatim(user_agent="geoplant_dashboard")
        location = geolocator.reverse(
            (lat, lon), language="en", zoom=3
        )  # zoom=3 gives country level
        if location:
            return location.address.split(",")[
                -1
            ].strip()  # Get the last part (Country)
        return "Unknown Location"
    except:
        return "Unknown Location"


# =========================================================
# 5. PUBLIC API
# =========================================================
def analyze_suitability(plant_name, lat, lon):
    conn = get_db_connection()
    if not conn:
        return {"error": "DB Error"}

    cur = conn.cursor()
    climate = fetch_climate_data(cur, lat, lon)
    conn.close()

    plant = get_plant_rules(plant_name)

    if not climate:
        return {"error": "Ocean/No Data"}

    score, status, reasons = calculate_score_logic(plant, climate)

    loc_name = get_location_name(lat, lon)  # get country location
    return {
        "score": score,
        "status": status,
        "reasons": reasons,
        "climate": climate,
        "plant": plant,
        "location_name": loc_name,
    }


def scan_continent_heatmap(plant_name, center_lat, center_lon, num_samples=200):
    """GLOBAL SCAN: Checks ~190 countries (1 point each)"""
    print("--- STARTING GLOBAL SCAN ---")
    plant = get_plant_rules(plant_name)
    if not plant:
        return pd.DataFrame()

    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()
    cur = conn.cursor()

    results = []

    # Loop through the GLOBAL dictionary
    for country, (lat, lon) in WORLD_LOCATIONS.items():
        climate = fetch_climate_data(cur, lat, lon)
        if climate:
            score, _, _ = calculate_score_logic(plant, climate)
            results.append({"country": country, "lat": lat, "lon": lon, "score": score})

    conn.close()
    print(f"--- SCAN COMPLETE: {len(results)} countries analyzed ---")
    return pd.DataFrame(results)


def get_top_countries(plant_name, scan_df):
    if scan_df.empty:
        return pd.DataFrame(columns=["country", "avg_score"])
    # No need to group by, scan_df already has unique countries
    # Just sort and return
    return (
        scan_df.sort_values("score", ascending=False)
        .head(10)
        .rename(columns={"score": "avg_score"})
    )
