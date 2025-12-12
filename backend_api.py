import psycopg2
import os
import numpy as np
import pandas as pd  # <--- FIXED: Added this missing import


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

    # CRITICAL FIX: Cast numpy floats to standard python floats
    # This prevents the "schema np does not exist" error
    lat = float(lat)
    lon = float(lon)

    # Query 6 tables
    # Note: We use ST_Value. If the point is in the ocean, it returns NULL.
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

        # Unit Conversion (Standard CHELSA V2.1)
        # Temp = Kelvin * 10
        def c_temp(val):
            if val is None:
                return 0
            if val > 1000:
                return (val / 10.0) - 273.15
            return val / 10.0

        # Rain = mm (sometimes scaled by 10)
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
            # Mocks for missing layers
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

    # Logic
    if climate["min_temp"] < plant["Min_Temp"]:
        score = 0
        status = "Dead"
        reasons.append(
            f"❄️ Too Cold: {climate['min_temp']}°C (Needs > {plant['Min_Temp']}°C)"
        )
    elif climate["rain"] < plant["Min_Rain"]:
        score -= 40
        status = "Risk"
        reasons.append("🌵 Too Dry")
    elif climate["max_temp"] > plant["Max_Temp"]:
        score -= 20
        status = "Stress"
        reasons.append("🔥 Heat Stress")
    elif climate["rain"] > plant["Max_Rain"]:
        score -= 10
        reasons.append("💧 Too Wet")

    return {
        "score": max(0, score),
        "status": status,
        "reasons": reasons,
        "climate": climate,
        "plant": plant,
    }


def scan_region(plant_name, center_lat, center_lon):
    """Scans 25 points around the center (5x5 grid)"""
    results = []
    # Create grid: +/- 1.0 degree (approx 100km box)
    offsets = np.linspace(-1.0, 1.0, 5)

    for lat_off in offsets:
        for lon_off in offsets:
            lat = center_lat + lat_off
            lon = center_lon + lon_off
            res = analyze_suitability(plant_name, lat, lon)

            if "error" not in res:
                # Color code for st.map
                # Green (00FF00) for high score, Red (FF0000) for low
                color = "#00FF00" if res["score"] > 50 else "#FF0000"

                results.append(
                    {
                        "lat": lat,
                        "lon": lon,
                        "score": res["score"],
                        "color": color,
                        # Scaling size for visual effect
                        "size": 100 if res["score"] > 50 else 20,
                    }
                )

    # Return empty DF if no results to prevent crashes
    if not results:
        return pd.DataFrame(columns=["lat", "lon", "score", "color", "size"])

    return pd.DataFrame(results)
