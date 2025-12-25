# 📖 GeoPlant User Manual

Welcome to GeoPlant! This dashboard allows you to analyze crop suitability anywhere in the world. This guide explains how to configure the analysis filters to get accurate results.

---

## 1. Selecting a Plant
GeoPlant allows you to choose from over 2,000 species imported from the FAO EcoCrop database.

* **How to use:** Click the dropdown and type to search. You can search by scientific name.
* **Example:** Try searching for **"Agropyron desertorum"** (Desert Wheatgrass).
* **Note:** If a plant is missing, it likely means the FAO did not have sufficient data for its survival thresholds.

---

## 2. Setting the Water Source
This filter is the most powerful tool for "Scenario Planning." It determines how the algorithm scores rainfall.

### 🌧️ Option A: Rainfed Only (Default)
* **Best for:** Traditional farming, dryland agriculture, or wild planting.
* **Logic:** The system strictly compares the location's natural rainfall against the plant's needs.
* **Scoring:** If the location receives 300mm of rain but the plant needs 600mm, the Suitability Score will drop significantly (likely to 0% or "Risk").
* **Chart Visual:** You will see a **Pink** shape on the Radar Chart. If the pink shape is smaller than the dotted line, the location is too dry.

### 💧 Option B: Irrigated
* **Best for:** Commercial farming, greenhouses, or home gardens with hoses/sprinklers.
* **Logic:** The system **ignores drought penalties**. We assume you will provide the missing water artificially.
* **Scoring:** A location that is naturally a desert (0% score) might jump to a **100% score** if the temperature is correct.
* **Chart Visual:** You will see a **Blue** overlay on the Radar Chart. This blue shape represents the "Artificial Climate" you created. The difference between the Pink (Natural) and Blue (Irrigated) shapes is your **Irrigation Bonus**.

---

## 3. Setting the Yield Target
This filter determines how strict the "Grading System" is.

### 🌱 Option A: Survival (Default)
* **Target Audience:** Hobbyists, Home Gardeners, Reforestation Projects.
* **Logic:** Uses the **Absolute Limits** of the plant.
* **Example:** *Agropyron desertorum* can technically survive at very low temperatures. In this mode, as long as the plant doesn't freeze to death or dry out completely, it gets a passing score (Green/Yellow). It answers the question: *"Will it stay alive?"*

### 💰 Option B: Max Yield (Strict)
* **Target Audience:** Commercial Farmers looking for profit.
* **Logic:** Uses the **Optimal Range** (The "Goldilocks Zone").
* **Example:** While *Agropyron* might survive at 5°C, it grows fastest at 15°C. In this mode, a location with 5°C will get a **Low Score (Red/Orange)** because the yield would be poor. It answers the question: *"Will I make money?"*

---

## 4. Understanding the Results
After clicking **RUN GLOBAL ANALYSIS**, the dashboard updates with three key insights:

1.  **Suitability Gauge (The Score):**
    * **0-45 (Red):** Not suitable. High risk of crop failure.
    * **46-79 (Yellow):** Stressful. The plant will grow but requires care or will have lower yields.
    * **80-100 (Green):** Ideal. The location matches the plant's biological needs perfectly.

2.  **Top Regions Chart (The Benchmark):**
    * This bar chart scans 190+ countries to find the best places on Earth for your selected plant.
    * **Your Location:** Look for the **Bold Black Bar**. This shows exactly where your chosen location ranks compared to the global leaders.
    * *Insight:* If the top country is 100% and you are 40%, you know you are fighting an uphill battle.

3.  **Global Map:**
    * A heatmap showing where else in the world this plant grows well.
    * **Green Areas:** High Suitability (>75).
    * **Blue Areas:** Moderate Suitability.
    * **Pink Areas:** Low Suitability.

## 5. Example Use Cases (Demo Scripts)

Use these scenarios to test the dashboard's capabilities.

### Scenario A: The "Microclimate" Detective (Precision Test)
*Demonstrates how location precision matters (Coast vs. Desert).*

* **Plant:** *Agropyron desertorum* (Desert Wheatgrass)
* **Settings:** Rainfed Only / Survival
* **Action 1:** Click on **Northern Algeria** (near the coast/Algiers).
    * **Result:** **Moderate Suitability (~60%)**. The Mediterranean breeze keeps winters mild (above 5°C).
* **Action 2:** Click on **Central Algeria** (deep in the Sahara).
    * **Result:** **Suitability 0% (Dead)**.
    * **Why?** Check the "Reasons". Even though it is a desert plant, the deep desert has freezing nights (3.8°C), killing the plant.
* **Takeaway:** GeoPlant detects local microclimates that generic "Country Averages" miss.

### Scenario B: The "Irrigation Simulator" (What-If Analysis)
*Demonstrates how farmers can solve drought problems.*

* **Plant:** *Hordeum vulgare* (Barley)
* **Location:** **Egypt** (near the Nile Delta).
* **Step 1 (Rainfed):**
    * **Result:** **Score 0-10% (Red)**.
    * **Reason:** Egypt has ~2mm of rain. Barley needs 200mm. It dies of thirst.
* **Step 2 (Change Filter):** Switch Water Source to **"Irrigated"**.
    * **Result:** **Score 100% (Green)**.
    * **Why?** The Temperature in Egypt is actually perfect for Barley (above 2°C). Once you artificially fix the water deficit, the location becomes ideal.

### Scenario C: The "Climate Barrier" (Biological Limits)
*Demonstrates that some factors (Temperature) cannot be fixed.*

* **Plant:** *Olea europaea* (Olive Tree)
* **Location:** **Germany** (vs. Italy).
* **Action:** Click anywhere in Germany.
    * **Result:** **Score 0% (Dead)**.
    * **Reason:** "❄️ Too Cold". Olives die if winter drops below 5°C. Germany is too cold.
* **Try Filters:** Switch to "Irrigated".
    * **Result:** **Still 0%**.
    * **Takeaway:** You can irrigate a dry plant, but you cannot easily heat a frozen country. This shows the tool's biological accuracy (Liebig's Law of the Minimum).
