import pandas as pd
from sqlalchemy import create_engine
import re

# ==========================================
# 1. CONFIGURATION
# ==========================================
INPUT_CSV = 'plants.csv' 
# OLD (Laptop to Docker):
# DB_CONNECTION = 'postgresql://postgres:admin@localhost:5432/geoplant'

# NEW (Docker to Docker):
DB_CONNECTION = 'postgresql://postgres:admin@geoplant_db:5432/geoplant'

# ==========================================
# 2. CLEANING LOGIC
# ==========================================
def extract_min_temp(text):
    # Search for numbers in the 'Growth' column
    # Handles "65-75 F" or similar
    matches = re.findall(r'(\d+)', str(text))
    if matches:
        # Assume numbers are Fahrenheit if > 40, else Celsius
        # Take the lowest number found as the Minimum
        val = float(min(matches, key=float))
        
        if val > 40: # Convert Fahrenheit to Celsius
            celsius = (val - 32) * 5/9
            return round(celsius, 1)
        else:
            return round(val, 1)
            
    # Fallbacks based on keywords if no numbers found
    text_lower = str(text).lower()
    if 'tropical' in text_lower: return 18.0
    if 'hardy' in text_lower: return -5.0
    return 10.0 # Default

def extract_rain(text):
    text = str(text).lower()
    if 'frequent' in text or 'moist' in text: return 1200
    if 'moderate' in text: return 800
    if 'dry' in text or 'scant' in text: return 300
    return 600 # Default

# ==========================================
# 3. EXECUTION
# ==========================================
try:
    print(f"Reading {INPUT_CSV}...")
    
    # FIX 1: encoding='cp1252' handles the Windows characters
    try:
        df = pd.read_csv(INPUT_CSV, encoding='cp1252')
    except:
        # Fallback if cp1252 fails
        df = pd.read_csv(INPUT_CSV, encoding='latin1')
    
    # Create empty dataframe for the database
    clean_df = pd.DataFrame()
    
    # FIX 2: Correct Column Mapping
    clean_df['name'] = df['Plant Name']  
    
    print("Extracting biological rules...")
    clean_df['min_temp_c'] = df['Growth'].apply(extract_min_temp)
    clean_df['max_temp_c'] = clean_df['min_temp_c'] + 15  # Estimate Max
    
    clean_df['min_rain_mm'] = df['Watering'].apply(extract_rain)
    clean_df['max_rain_mm'] = clean_df['min_rain_mm'] + 1000
    
    # Add dummy pH
    clean_df['min_ph'] = 6.0
    clean_df['max_ph'] = 7.5

    # Check for empty names and drop them
    clean_df = clean_df.dropna(subset=['name'])

    print("Data Cleaned. Example row:")
    print(clean_df.iloc[0])

    print("\nUploading to Database...")
    engine = create_engine(DB_CONNECTION)
    clean_df.to_sql('plants', engine, if_exists='replace', index=False)
    
    print("✅ SUCCESS! Table 'plants' created.")

except Exception as e:
    print(f"❌ ERROR: {e}")
