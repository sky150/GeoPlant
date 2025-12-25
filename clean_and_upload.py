import pandas as pd
from sqlalchemy import create_engine, text
import numpy as np
import os

# ==========================================
# 1. CONFIGURATION
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_CSV = os.path.join(BASE_DIR, "data", "EcoCrop_DB.csv")

DB_CONNECTION = "postgresql://postgres:admin@geoplant_db:5432/geoplant"


# ==========================================
# 2. CLEANING LOGIC
# ==========================================
def clean_ecocrop():
    print(f"Reading {INPUT_CSV}...")

    try:
        df = pd.read_csv(INPUT_CSV, encoding="utf-8")
    except:
        df = pd.read_csv(INPUT_CSV, encoding="latin1")

    # 1. Map Columns
    col_map = {
        "ScientificName": "name",
        "TMIN": "min_temp_c",
        "TMAX": "max_temp_c",
        "RMIN": "min_rain_mm",
        "RMAX": "max_rain_mm",
        "PHMIN": "min_ph",
        "PHMAX": "max_ph",
        "TOPMN": "opt_min_temp_c",
        "TOPMX": "opt_max_temp_c",
        "ROPMN": "opt_min_rain_mm",
        "ROPMX": "opt_max_rain_mm",
        "PHOPMN": "opt_min_ph",
        "PHOPMX": "opt_max_ph",
    }

    df = df.rename(columns=col_map)
    available_cols = [c for c in col_map.values() if c in df.columns]
    df = df[available_cols]

    # 2. Handle "NA"
    df.replace(["NA", "na", "", " "], np.nan, inplace=True)

    # 3. Numeric Conversion
    numeric_cols = [c for c in available_cols if c != "name"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 4. Cleanup
    critical_cols = ["min_temp_c", "max_temp_c", "min_rain_mm", "max_rain_mm"]
    df = df.dropna(subset=critical_cols)
    df = df.dropna(subset=["name"])

    # 5. Fill Missing Optimal Values
    df["opt_min_temp_c"] = df["opt_min_temp_c"].fillna(df["min_temp_c"])
    df["opt_max_temp_c"] = df["opt_max_temp_c"].fillna(df["max_temp_c"])
    df["opt_min_rain_mm"] = df["opt_min_rain_mm"].fillna(df["min_rain_mm"])
    df["opt_max_rain_mm"] = df["opt_max_rain_mm"].fillna(df["max_rain_mm"])

    df["min_ph"] = df["min_ph"].fillna(5.5)
    df["max_ph"] = df["max_ph"].fillna(7.5)
    df["opt_min_ph"] = df["opt_min_ph"].fillna(6.0)
    df["opt_max_ph"] = df["opt_max_ph"].fillna(7.0)

    print(f"Cleaned Row Count: {len(df)}")
    return df


# ==========================================
# 3. UPLOAD & TABLE CREATION
# ==========================================
if __name__ == "__main__":
    try:
        clean_df = clean_ecocrop()

        if clean_df.empty:
            print("⚠️ WARNING: No plants left after cleaning!")
        else:
            print("\nRecreating Database Table...")
            engine = create_engine(DB_CONNECTION)

            # --- NEU: Tabelle per SQL erstellen ---
            create_table_sql = """
            DROP TABLE IF EXISTS plants;
            CREATE TABLE plants (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255),
                min_temp_c FLOAT, max_temp_c FLOAT,
                opt_min_temp_c FLOAT, opt_max_temp_c FLOAT,
                min_rain_mm INT, max_rain_mm INT,
                opt_min_rain_mm INT, opt_max_rain_mm INT,
                min_ph FLOAT, max_ph FLOAT,
                opt_min_ph FLOAT, opt_max_ph FLOAT
            );
            """

            with engine.connect() as con:
                con.execute(text(create_table_sql))
                con.commit()

            print("Table created. Inserting data...")
            clean_df.to_sql("plants", engine, if_exists="append", index=False)

            print(f"✅ SUCCESS! {len(clean_df)} plants loaded.")

    except Exception as e:
        print(f"❌ ERROR: {e}")
