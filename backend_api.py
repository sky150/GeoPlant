import psycopg2
import os
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
# 2. LOGIC
# =========================================================


def _calculate_single_score(plant, climate, ignore_drought=False, use_optimal=False):
    """
    Calculates score based on either Absolute Limits (Survival)
    OR Optimal Ranges (Thriving).
    """
    score = 100
    reasons = []
    status = "Ideal"

    # Select which rules to use based on the filter
    if use_optimal:
        # STRICT MODE (Commercial Yield)
        t_min = plant["Opt_Min_Temp"]
        t_max = plant["Opt_Max_Temp"]
        r_min = plant["Opt_Min_Rain"]
        r_max = plant["Opt_Max_Rain"]
    else:
        # RELAXED MODE (Survival)
        t_min = plant["Min_Temp"]
        t_max = plant["Max_Temp"]
        r_min = plant["Min_Rain"]
        r_max = plant["Max_Rain"]

    # 1. Temperature Check
    if climate["min_temp"] < t_min:
        score = 0
        status = "Dead" if not use_optimal else "Low Yield"
        reasons.append(f"❄️ Too Cold: {climate['min_temp']}°C < {t_min}°C")
        return 0, status, reasons  # Stop checking if temp fails

    if climate["max_temp"] > t_max:
        score -= 20
        status = "Stress"
        reasons.append(f"🔥 Too Hot: {climate['max_temp']}°C > {t_max}°C")

    # 2. Water Check
    if climate["rain"] < r_min:
        if not ignore_drought:
            score -= 40
            status = "Risk"
            reasons.append(f"🌵 Too Dry: {climate['rain']}mm < {r_min}mm")

    if climate["rain"] > r_max:
        score -= 10
        reasons.append(f"💧 Too Wet: {climate['rain']}mm > {r_max}mm")

    return max(0, int(score)), status, reasons


def calculate_score_logic(
    plant, climate, water_source="Rainfed Only", yield_goal="Survival"
):
    if not climate or not plant:
        return 0, "Error", [], 0

    # Determine strictness
    use_optimal = yield_goal == "Max Yield (Strict)"

    # 1. Calculate Natural Score
    score_nat, status_nat, reasons_nat = _calculate_single_score(
        plant, climate, ignore_drought=False, use_optimal=use_optimal
    )

    # 2. Calculate Irrigated Score
    score_irr, status_irr, reasons_irr = _calculate_single_score(
        plant, climate, ignore_drought=True, use_optimal=use_optimal
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
    query = """
        SELECT min_temp_c, max_temp_c, min_rain_mm, max_rain_mm, min_ph, max_ph, opt_min_temp_c, opt_max_temp_c, opt_min_rain_mm, opt_max_rain_mm, opt_min_ph, opt_max_ph
        FROM plants WHERE name = %s
    """
    cur.execute(query, (plant_name,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None

    return {
        "name": plant_name,
        # Absolute Limits
        "Min_Temp": row[0],
        "Max_Temp": row[1],
        "Min_Rain": row[2],
        "Max_Rain": row[3],
        "Min_pH": row[4],
        "Max_pH": row[5],
        # Optimal Ranges
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
        return "Unknown"
    except:
        return "Unknown"


# =========================================================
# 5. PUBLIC API
# =========================================================
def analyze_suitability(
    plant_name, lat, lon, water_source="Rainfed Only", yield_goal="Survival"
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

    score, status, reasons, bonus = calculate_score_logic(
        plant, climate, water_source, yield_goal
    )
    loc_name = get_location_name(lat, lon)

    return {
        "score": score,
        "status": status,
        "reasons": reasons,
        "bonus": bonus,
        "climate": climate,
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
            # Fixed unpacking error
            score = calculate_score_logic(plant, climate, "Rainfed Only", "Survival")[0]
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
