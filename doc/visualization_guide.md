# 📈 Visualization Guide

GeoPlant uses specific charts to communicate "Suitability" and "Risk." Here is how to interpret them.

## 1. Suitability Gauge
**What it shows:** The final "Score" (0-100) of the location.
* **Green Ring:** The Natural Score (based on rainfall and temp).
* **Blue Segment:** The **Irrigation Bonus**. If you see a blue section, it means "The location is naturally dry, but if you add water, the suitability jumps up by this amount."

## 2. Conditions Radar
**What it shows:** A comparison of the Location (Color) vs. the Plant's Optimum (Dotted Line).

* **Pink Shape (Natural Climate):** This represents the location's natural condition.
    * *Inside the Dotted Line:* The location is lacking (too cold, too dry).
    * *Outside the Dotted Line:* The location has excess (too hot, too wet).
    * *On the Dotted Line:* Perfect match.
* **Blue Shape (With Irrigation):** If you enable Irrigation, a blue shape appears. You will usually see the "Rain" axis extend out to the dotted line, visually proving that you have artificially fixed the water deficit.

## 3. Deviation Bar Chart
**What it shows:** Exactly how far "off" the location is from perfection.

* **Center (0%):** Perfect Match.
* **Left (Blue Bars):** Deficit. (e.g., -20% Rain means you have 20% less rain than the plant wants).
* **Right (Pink Bars):** Excess. (e.g., +10% Temp means it is slightly hotter than optimal).

**Tip:** "Blue" bars on the left (Deficits) can often be fixed by humans (Greenhouses, Irrigation). "Pink" bars on the right (Excesses) are often impossible to fix (you cannot air-condition a corn field).
