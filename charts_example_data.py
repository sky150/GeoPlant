import pandas as pd
import numpy as np

CONDITIONS = ["Temperature", "Precipitation", "Sunlight", "Soil Moisture", "pH"]

plants = ["Tomato", "Blueberry", "Cactus"]

plant_requirements = pd.DataFrame([
    #        plant       condition         optimum (0–100)
    ("Tomato",   "Temperature",      75),
    ("Tomato",   "Precipitation",    65),
    ("Tomato",   "Sunlight",         85),
    ("Tomato",   "Soil Moisture",    70),
    ("Tomato",   "pH",               60),

    ("Blueberry","Temperature",      60),
    ("Blueberry","Precipitation",    80),
    ("Blueberry","Sunlight",         70),
    ("Blueberry","Soil Moisture",    75),
    ("Blueberry","pH",               50),

    ("Cactus",   "Temperature",      85),
    ("Cactus",   "Precipitation",    20),
    ("Cactus",   "Sunlight",         95),
    ("Cactus",   "Soil Moisture",    25),
    ("Cactus",   "pH",               55),
], columns=["plant", "condition", "plant_optimum"])

location_climate = pd.DataFrame([
    #  location     lat    lon    condition         local_value
    ("Valencia",   39.5,  -0.4,  "Temperature",    80),
    ("Valencia",   39.5,  -0.4,  "Precipitation",  40),
    ("Valencia",   39.5,  -0.4,  "Sunlight",       90),
    ("Valencia",   39.5,  -0.4,  "Soil Moisture",  50),
    ("Valencia",   39.5,  -0.4,  "pH",             65),

    ("Hamburg",    53.6,   9.9,  "Temperature",    55),
    ("Hamburg",    53.6,   9.9,  "Precipitation",  75),
    ("Hamburg",    53.6,   9.9,  "Sunlight",       60),
    ("Hamburg",    53.6,   9.9,  "Soil Moisture",  80),
    ("Hamburg",    53.6,   9.9,  "pH",             55),

    ("Cairo",      30.0,  31.2,  "Temperature",    90),
    ("Cairo",      30.0,  31.2,  "Precipitation",  10),
    ("Cairo",      30.0,  31.2,  "Sunlight",       95),
    ("Cairo",      30.0,  31.2,  "Soil Moisture",  20),
    ("Cairo",      30.0,  31.2,  "pH",             60),
], columns=["location", "lat", "lon", "condition", "local_value"])

#plant_optimum vs local_value
#diverging difference (x) vs conditions (y)
def get_plant_location_profile(plant: str, location: str) -> pd.DataFrame:
    """Gibt ein DataFrame mit allen Bedingungen für (Pflanze, Ort) zurück:
       Spalten: condition, plant_optimum, local_value, difference
    """
    plant_df = plant_requirements[plant_requirements["plant"] == plant]
    loc_df = location_climate[location_climate["location"] == location]

    merged = pd.merge(
        plant_df,
        loc_df[["location", "condition", "local_value"]],
        on="condition",
        how="inner",
        validate="one_to_one",
    )

    merged["difference"] = merged["local_value"] - merged["plant_optimum"]
    return merged

#bubble map
def compute_location_scores_for_plant(plant: str) -> pd.DataFrame:
    """Berechnet pro Ort einen 'growth_score' (0–100) für die gegebene Pflanze."""
    plant_df = plant_requirements[plant_requirements["plant"] == plant]

    merged = pd.merge(
        location_climate,
        plant_df[["condition", "plant_optimum"]],
        on="condition",
        how="inner",
        validate="many_to_one",
    )

    # simple scoring: 100 - |local - optimum|, gekappt auf [0, 0..100]
    merged["score_per_condition"] = 100 - (merged["local_value"] - merged["plant_optimum"]).abs()
    merged["score_per_condition"] = merged["score_per_condition"].clip(lower=0, upper=100)

    # pro Ort Mittelwert über alle Bedingungen
    scores = (
        merged.groupby(["location", "lat", "lon"], as_index=False)["score_per_condition"]
        .mean()
        .rename(columns={"score_per_condition": "growth_score"})
    )

    return scores

