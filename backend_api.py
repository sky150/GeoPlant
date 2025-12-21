import psycopg2
import os
import numpy as np
import pandas as pd
from countries import WORLD_LOCATIONS
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


def get_seasonal_climate(climate, season):
    """Adjusts min/max temp based on growing season."""
    if season == "Year Round":
        return climate

    # Extract annual extremes
    min_t = climate["min_temp"]
    max_t = climate["max_temp"]

    # Simulate 12 months (0=Jan, 6=July)
    months = np.arange(12)
    mean = (max_t + min_t) / 2
    amp = (max_t - min_t) / 2

    # Cosine wave simulation
    monthly_temps = mean - amp * np.cos(months * 2 * np.pi / 12)

    # Filter indices based on season
    if "Spring" in season:
        indices = [2, 3, 4, 5]
    elif "Summer" in season:
        indices = [5, 6, 7, 8]
    elif "Autumn" in season:
        indices = [8, 9, 10]
    elif "Winter" in season:
        indices = [11, 0, 1, 2]
    else:
        indices = range(12)

    season_temps = monthly_temps[indices]

    new_climate = climate.copy()
    new_climate["min_temp"] = float(round(np.min(season_temps), 1))
    new_climate["max_temp"] = float(round(np.max(season_temps), 1))

    return new_climate


def _calculate_single_score(plant, climate, ignore_drought=False):
    """Calculates score based on Absolute Limits (Survival)."""
    score = 100
    reasons = []
    status = "Ideal"

    # 1. Winter Kill (Absolute Limit)
    if climate["min_temp"] < plant["Min_Temp"]:
        score = 0
        status = "Dead"
        reasons.append(f"❄️ Freeze: {climate['min_temp']:.1f}°C")
        return 0, status, reasons  # Stop checking

    # 2. Drought
    if climate["rain"] < plant["Min_Rain"]:
        if not ignore_drought:
            score -= 40
            status = "Risk"
            reasons.append(f"🌵 Dry: {climate['rain']}mm")

    # 3. Heat
    if climate["max_temp"] > plant["Max_Temp"]:
        score -= 20
        if status == "Ideal":
            status = "Stress"
        reasons.append(f"🔥 Hot: {climate['max_temp']:.1f}°C")

    # 4. Wet
    if climate["rain"] > plant["Max_Rain"]:
        score -= 10
        if status == "Ideal":
            status = "Tolerable"
        reasons.append(f"💧 Wet: {climate['rain']}mm")

    return max(0, int(score)), status, reasons


def calculate_score_logic(plant, climate, water_source="Rainfed Only"):
    if not climate or not plant:
        return 0, "Error", [], 0

    # 1. Calculate Natural Score
    score_nat, status_nat, reasons_nat = _calculate_single_score(
        plant, climate, ignore_drought=False
    )

    # 2. Calculate Irrigated Score
    score_irr, status_irr, reasons_irr = _calculate_single_score(
        plant, climate, ignore_drought=True
    )

    # 3. Apply Logic
    if water_source == "Irrigated":
        final_score = score_irr
        final_status = status_irr
        final_reasons = reasons_irr
        bonus = max(0, score_irr - score_nat)
        if bonus > 0:
            final_reasons.append(f"💧 Irrigation Bonus: +{bonus}")
    else:
        final_score = score_nat
        final_status = status_nat
        final_reasons = reasons_nat
        bonus = 0

    return final_score, final_status, final_reasons, bonus


# =========================================================
# 3. DATA FETCHING
# =========================================================
def fetch_climate_data(cursor, lat, lon):
    lat, lon = float(lat), float(lon)
    query = """
    SELECT 
        ST_Value(mean.rast, ST_SetSRID(ST_Point(%s, %s), 4326)),
        ST_Value(min.rast, ST_SetSRID(ST_Point(%s, %s), 4326)),
        ST_Value(max.rast, ST_SetSRID(ST_Point(%s, %s), 4326)),
        ST_Value(rain.rast, ST_SetSRID(ST_Point(%s, %s), 4326)),
        ST_Value(dry.rast, ST_SetSRID(ST_Point(%s, %s), 4326)),
        ST_Value(seas.rast, ST_SetSRID(ST_Point(%s, %s), 4326))
    FROM climate_temp_mean mean, climate_temp_min min, climate_temp_max max,
         climate_rain rain, climate_rain_driest dry, climate_rain_seasonality seas
    WHERE ST_Intersects(mean.rast, ST_SetSRID(ST_Point(%s, %s), 4326)) AND
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

        def val(idx, scale=10.0, offset=0):
            v = row[idx]
            if v is None:
                return 0
            if scale == 10.0 and v > 1000:
                return (v / 10.0) - 273.15
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
# 4. PLANT DATA & UTILS
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
    # Updated query to fetch optimal values too
    query = """
        SELECT min_temp_c, max_temp_c, min_rain_mm, max_rain_mm, min_ph, max_ph,
               opt_min_temp_c, opt_max_temp_c, opt_min_rain_mm, opt_max_rain_mm, 
               opt_min_ph, opt_max_ph
        FROM plants WHERE name = %s
    """
    cur.execute(query, (plant_name,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None

    return {
        "name": plant_name,
        # Absolute Limits (Used for Survival Checks)
        "Min_Temp": row[0],
        "Max_Temp": row[1],
        "Min_Rain": row[2],
        "Max_Rain": row[3],
        "Min_pH": row[4],
        "Max_pH": row[5],
        # Optimal Ranges (Added for future use) - Fallback to Absolute if NULL
        "Opt_Min_Temp": row[6] if row[6] is not None else row[0],
        "Opt_Max_Temp": row[7] if row[7] is not None else row[1],
        "Opt_Min_Rain": row[8] if row[8] is not None else row[2],
        "Opt_Max_Rain": row[9] if row[9] is not None else row[3],
        "Opt_Min_pH": row[10] if row[10] is not None else row[4],
        "Opt_Max_pH": row[11] if row[11] is not None else row[5],
        "Ideal_Hum": 50,
        "Sun_Need": 80,
    }


def get_location_name(lat, lon):
    try:
        geolocator = Nominatim(user_agent="geoplant_dashboard")
        location = geolocator.reverse((lat, lon), language="en", zoom=3)
        if location:
            return location.address.split(",")[-1].strip()
        return "Unknown Location"
    except:
        return "Unknown Location"


# =========================================================
# 5. PUBLIC API
# =========================================================
def analyze_suitability(
    plant_name, lat, lon, water_source="Rainfed Only", planting_season="Year Round"
):
    conn = get_db_connection()
    if not conn:
        return {"error": "DB Error"}

    cur = conn.cursor()
    climate = fetch_climate_data(cur, lat, lon)
    conn.close()

    plant = get_plant_rules(plant_name)

    if not climate:
        return {"error": "Ocean/No Data"}

    # Apply Seasonal Adjustment
    climate_adjusted = get_seasonal_climate(climate, planting_season)

    score, status, reasons, bonus = calculate_score_logic(
        plant, climate_adjusted, water_source
    )
    loc_name = get_location_name(lat, lon)

    return {
        "score": score,
        "status": status,
        "reasons": reasons,
        "bonus": bonus,
        "climate": climate_adjusted,
        "plant": plant,
        "location_name": loc_name,
        "water_source": water_source,
    }


def scan_continent_heatmap(plant_name, center_lat, center_lon, num_samples=200):
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()
    cur = conn.cursor()
    plant = get_plant_rules(plant_name)
    results = []

    for country, (lat, lon) in WORLD_LOCATIONS.items():
        climate = fetch_climate_data(cur, lat, lon)
        if climate:
            # Only extract score
            score = calculate_score_logic(plant, climate, "Rainfed Only")[0]
            results.append({"country": country, "lat": lat, "lon": lon, "score": score})

    conn.close()
    return pd.DataFrame(results)


def get_top_countries(plant_name, scan_df):
    if scan_df.empty:
        return pd.DataFrame(columns=["country", "avg_score"])
    return (
        scan_df.sort_values("score", ascending=False)
        .head(10)
        .rename(columns={"score": "avg_score"})
    )
