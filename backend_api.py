import psycopg2
import os
import numpy as np

def get_db_connection():
    try:
        return psycopg2.connect(
            host=os.getenv("DB_HOST", "geoplant_db"),
            database=os.getenv("DB_NAME", "geoplant"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASS", "admin")
        )
    except Exception as e:
        print(f"DB Connection Error: {e}")
        return None

def get_real_climate(lat, lon):
    """
    Queries 6 Raster tables: Mean, Min, Max, Rain, Driest Quarter, Seasonality
    """
    conn = get_db_connection()
    if not conn: return None

    # We now query 6 tables
    query = """
    SELECT 
        ST_Value(mean.rast, ST_SetSRID(ST_Point(%s, %s), 4326)) as raw_mean,
        ST_Value(min.rast, ST_SetSRID(ST_Point(%s, %s), 4326)) as raw_min,
        ST_Value(max.rast, ST_SetSRID(ST_Point(%s, %s), 4326)) as raw_max,
        ST_Value(rain.rast, ST_SetSRID(ST_Point(%s, %s), 4326)) as raw_rain,
        ST_Value(dry.rast, ST_SetSRID(ST_Point(%s, %s), 4326)) as raw_dry,
        ST_Value(seas.rast, ST_SetSRID(ST_Point(%s, %s), 4326)) as raw_season
    FROM 
        climate_temp_mean mean,
        climate_temp_min min,
        climate_temp_max max,
        climate_rain rain,
        climate_rain_driest dry,
        climate_rain_seasonality seas
    WHERE 
        ST_Intersects(mean.rast, ST_SetSRID(ST_Point(%s, %s), 4326)) AND
        ST_Intersects(min.rast, ST_SetSRID(ST_Point(%s, %s), 4326)) AND
        ST_Intersects(max.rast, ST_SetSRID(ST_Point(%s, %s), 4326)) AND
        ST_Intersects(rain.rast, ST_SetSRID(ST_Point(%s, %s), 4326)) AND
        ST_Intersects(dry.rast, ST_SetSRID(ST_Point(%s, %s), 4326)) AND
        ST_Intersects(seas.rast, ST_SetSRID(ST_Point(%s, %s), 4326));
    """
    
    cur = conn.cursor()
    # Pass lon/lat 12 times (2 times for each of the 6 tables)
    args = (lon, lat) * 12
    
    try:
        cur.execute(query, args)
        result = cur.fetchone()
        conn.close()
        
        if not result or result[0] is None:
            return None

        # --- UNIT CONVERSIONS ---
        def convert_temp(val):
            # Handles Kelvin * 10 vs Celsius * 10
            if val > 1000: return (val / 10.0) - 273.15
            elif val > 100: return val - 273.15
            else: return val / 10.0

        def convert_rain(val):
            # Handles large rain scaling
            if val > 5000: return val / 10.0
            return val

        climate_data = {
            "mean_temp": round(convert_temp(result[0]), 1),
            "min_temp":  round(convert_temp(result[1]), 1),
            "max_temp":  round(convert_temp(result[2]), 1),
            "rain":      int(convert_rain(result[3])),
            
            # NEW DATA
            "driest_month_rain": int(convert_rain(result[4])), # Bio17
            "seasonality": int(result[5]),                     # Bio15 (Coefficient, no units)
            
            # Still Mocked (SoilGrids is too hard for now)
            "ph": 6.5,          
            "humidity": 60,     
            "sun": 80,          
            "elevation": 500    
        }
        return climate_data

    except Exception as e:
        print(f"SQL Error: {e}")
        return None

def get_plant_list():
    conn = get_db_connection()
    if not conn: return []
    cur = conn.cursor()
    cur.execute("SELECT name FROM plants ORDER BY name ASC")
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_plant_rules(plant_name):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT min_temp_c, max_temp_c, min_rain_mm, max_rain_mm, min_ph, max_ph 
        FROM plants WHERE name = %s
    """, (plant_name,))
    row = cur.fetchone()
    conn.close()
    
    if not row: return None
    
    return {
        "name": plant_name,
        "Min_Temp": row[0], "Max_Temp": row[1],
        "Min_Rain": row[2], "Max_Rain": row[3],
        "Min_pH": row[4],   "Max_pH": row[5],
        "Ideal_Hum": 50, "Sun_Need": 80, "Max_Elev": 2000 
    }

def analyze_suitability(plant_name, lat, lon):
    
    climate = get_real_climate(lat, lon)
    plant = get_plant_rules(plant_name)
    
    if not climate: return {"error": "Location not found (Ocean?)."}
    if not plant: return {"error": "Plant data missing."}

    score = 100
    reasons = []
    status = "Ideal"

    # 1. WINTER KILL
    if climate['min_temp'] < plant['Min_Temp']:
        score = 0
        status = "Dead"
        reasons.append(f"❄️ CRITICAL: Freezing Winter ({climate['min_temp']}°C). Plant dies below {plant['Min_Temp']}°C.")

    # 2. ANNUAL DROUGHT
    elif climate['rain'] < plant['Min_Rain']:
        score -= 40
        status = "Risk"
        reasons.append(f"🌵 ANNUAL DROUGHT: Only {climate['rain']}mm rain/year (Needs {plant['Min_Rain']}mm).")

    # 3. *** NEW: SEASONAL DROUGHT STRESS ***
    # If plant needs lots of water (>1000mm) but the summer is dry (<50mm in driest quarter)
    elif plant['Min_Rain'] > 1000 and climate['driest_month_rain'] < 40:
        score -= 25
        if status == "Ideal": status = "Stressed"
        reasons.append(f"🏜️ SEASONAL DROUGHT: Summer is too dry ({climate['driest_month_rain']}mm rain in driest months). Irrigation needed.")

    # 4. HEAT STRESS
    elif climate['max_temp'] > plant['Max_Temp']:
        score -= 20
        status = "Stressed"
        reasons.append(f"🔥 HEAT STRESS: Summer hits {climate['max_temp']}°C.")
    
    # 5. WET FEET
    elif climate['rain'] > plant['Max_Rain']:
        score -= 10
        if status == "Ideal": status = "Tolerable"
        reasons.append(f"💧 TOO WET: {climate['rain']}mm rain (Prefers < {plant['Max_Rain']}mm).")

    return {
        "score": max(0, score),
        "status": status,
        "reasons": reasons,
        "climate": climate, 
        "plant": plant      
    }
