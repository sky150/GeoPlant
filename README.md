# 🌍 GeoPlant: Smart Crop Suitability Engine

**GeoPlant** is a Precision Agriculture dashboard that helps farmers and gardeners decide **where** to plant specific crops. It uses high-resolution climate rasters (CHELSA V2) and biological thresholds to calculate a "Survival Score" for any coordinate in Europe.

---

## 🏗️ Architecture

The app follows a **Service-Oriented Architecture** running on Docker:

1.  **Database Container (`geoplant_db`):**
    * Runs PostgreSQL + PostGIS.
    * Stores 50GB of Raster Data (Temperature, Rain, Drought metrics).
    * Stores the Plant Rules (CSV converted to SQL).
2.  **App Container (`geoplant_app`):**
    * Runs Python Streamlit.
    * **`backend_api.py` (The Brain):** Handles SQL connections and biological logic (e.g., "If Temp < 0, Plant Dies").
    * **`app.py` (The Face):** The User Interface, interactive map, and charts.

---

## 🛠️ Setup Guide (For New Developers)

### Step 1: Install Prerequisites
* [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Must be running).
* Git.

### Step 2: Clone & Prepare Folders
Clone this repository. Then, inside the folder, create a folder for the raw data (it is ignored by Git):

```bash
mkdir chelsa_raw
```

### Step 3: Download Raw Data (The "Heavy Lift")
We rely on **CHELSA V2.1**. You must download these 6 files (~2GB total) and place them inside the `chelsa_raw/` folder you just created.

| File Name (Bio Variable) | Why we need it? | Download Link |
| :--- | :--- | :--- |
| **Bio 01** (Mean Temp) | General climate baseline. | [Download Bio01](https://os.unil.cloud.switch.ch/chelsa02/chelsa/global/bioclim/bio01/1981-2010/CHELSA_bio01_1981-2010_V.2.1.tif) |
| **Bio 05** (Max Temp) | To detect Summer Heat Stress. | [Download Bio05](https://os.unil.cloud.switch.ch/chelsa02/chelsa/global/bioclim/bio05/1981-2010/CHELSA_bio05_1981-2010_V.2.1.tif) |
| **Bio 06** (Min Temp) | **CRITICAL:** Detects Winter Frost (Kill factor). | [Download Bio06](https://os.unil.cloud.switch.ch/chelsa02/chelsa/global/bioclim/bio06/1981-2010/CHELSA_bio06_1981-2010_V.2.1.tif) |
| **Bio 12** (Annual Rain) | General water availability. | [Download Bio12](https://os.unil.cloud.switch.ch/chelsa02/chelsa/global/bioclim/bio12/1981-2010/CHELSA_bio12_1981-2010_V.2.1.tif) |
| **Bio 15** (Seasonality) | Is rain stable or extreme? (Fungus risk). | [Download Bio15](https://os.unil.cloud.switch.ch/chelsa02/chelsa/global/bioclim/bio15/1981-2010/CHELSA_bio15_1981-2010_V.2.1.tif) |
| **Bio 17** (Driest Qtr) | **CRITICAL:** Detects Summer Droughts. | [Download Bio17](https://os.unil.cloud.switch.ch/chelsa02/chelsa/global/bioclim/bio17/1981-2010/CHELSA_bio17_1981-2010_V.2.1.tif) |

**Plant Data:**
Ensure `plants.csv` (Source: Kaggle) is in the main folder.

---

### Step 4: Launch the System
Open your terminal in the project folder and run:

```bash
docker-compose up -d --build
```
*Wait 2 minutes for Python to install dependencies.*

---

### Step 5: Data Ingestion (The One-Time Setup)
We need to load the Tiff files into the Database.

**A. Enter the Database Container:**

```bash
docker exec -it geoplant_db bash
```

**B. Install Import Tools (Inside Container):**

```bash
apt-get update && apt-get install -y postgis
```

**C. Run the Import Commands (Copy/Paste one by one):**
*Note: These might take 2-5 minutes each.*

```bash
# 1. Mean Temp
raster2pgsql -s 4326 -I -C -M -d -t 50x50 /raw_data/CHELSA_bio01_1981-2010_V.2.1.tif public.climate_temp_mean | psql -U postgres -d geoplant

# 2. Max Temp
raster2pgsql -s 4326 -I -C -M -d -t 50x50 /raw_data/CHELSA_bio05_1981-2010_V.2.1.tif public.climate_temp_max | psql -U postgres -d geoplant

# 3. Min Temp (Critical)
raster2pgsql -s 4326 -I -C -M -d -t 50x50 /raw_data/CHELSA_bio06_1981-2010_V.2.1.tif public.climate_temp_min | psql -U postgres -d geoplant

# 4. Annual Rain
raster2pgsql -s 4326 -I -C -M -d -t 50x50 /raw_data/CHELSA_bio12_1981-2010_V.2.1.tif public.climate_rain | psql -U postgres -d geoplant

# 5. Rain Seasonality
raster2pgsql -s 4326 -I -C -M -d -t 50x50 /raw_data/CHELSA_bio15_1981-2010_V.2.1.tif public.climate_rain_seasonality | psql -U postgres -d geoplant

# 6. Drought (Driest Quarter)
raster2pgsql -s 4326 -I -C -M -d -t 50x50 /raw_data/CHELSA_bio17_1981-2010_V.2.1.tif public.climate_rain_driest | psql -U postgres -d geoplant
```

**D. Exit the database container:**
Type `exit`.

---

### Step 6: Upload Plant Data
Now we run the Python script to clean the Kaggle CSV and put it in the database.

```bash
docker exec -it geoplant_app python clean_and_upload.py
```

---

## 🚀 Running the App
Once the setup is done, the app starts automatically!

**Go to: [http://localhost:8501](http://localhost:8501)**

## 📂 Code Structure Explained

* **`backend_api.py`**: The "Backend".
    * It contains the SQL queries (`SELECT ST_Value...`).
    * It performs unit conversion (Kelvin to Celsius).
    * It contains the **Suitability Algorithm** (e.g., Checking if Winter Low < Plant Minimum).
* **`app.py`**: The "Frontend".
    * It uses `streamlit` to draw buttons and layouts.
    * It uses `folium` for the interactive map.
    * It calls `backend_api.analyze_suitability()` to get the answers.
