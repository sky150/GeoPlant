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

It provides standardized environmental requirements for over 2,500 species, defining both "Optimal" growing conditions and "Absolute" physiological limits. This structure allows GeoPlant to calculate a nuanced suitability gradient (0–100%) based on how close the local climate is to the plant's ideal range, rather than a simple pass/fail metric.
