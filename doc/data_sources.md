# 📊 Data Sources & Methodology

GeoPlant relies on two primary scientific datasets to generate its suitability scores.

## 1. Climate Data: CHELSA V2.1
**Source:** [Swiss Federal Institute for Forest, Snow and Landscape Research (WSL)](https://chelsa-climate.org/)

We utilize **CHELSA (Climatologies at high resolution for the earth’s land surface areas)** version 2.1.

### Why CHELSA?
Standard global climate models often have a resolution of ~10km-20km. This is too coarse for precision agriculture (it might average a mountain peak with a valley).
CHELSA offers **1km resolution** by downscaling global models using topographical data. This allows GeoPlant to distinguish between a sunny south-facing slope and a freezing valley floor.

### Layers Used
* **Bio01 (Mean Annual Temp):** General baseline.
* **Bio06 (Min Temperature of Coldest Month):** Used to determine "Winter Kill" risk.
* **Bio05 (Max Temperature of Warmest Month):** Used to determine "Heat Stress."
* **Bio12 (Annual Precipitation):** Total water availability.
* **Bio17 (Precipitation of Driest Quarter):** Used to identify drought risks during growing seasons.

## 2. Biological Rules: FAO EcoCrop
**Source:** [Food and Agriculture Organization (FAO) - Archived by OpenCLIM](https://github.com/OpenCLIM/ecocrop)

We replaced generic crowd-sourced data with the **EcoCrop Database**. This dataset was built by the FAO specifically for Land Use Planning.

### The "Dual Threshold" Logic
Unlike simple datasets that provide a single "Temperature Range," EcoCrop provides two distinct sets of rules for over 2,000 species:

1.  **Absolute Limits (Survival):**
    * *Definition:* The temperature/rainfall beyond which the plant physically dies.
    * *GeoPlant Logic:* If location is outside these limits → **Score = 0% (Dead)**.

2.  **Optimal Range (Thriving):**
    * *Definition:* The "Goldilocks" zone where the plant produces maximum yield.
    * *GeoPlant Logic:* If location is inside these limits → **Score = 100% (Perfect)**.

This allows GeoPlant to simulate the difference between "Surviving" (Hobby gardening) and "Thriving" (Commercial Farming).
