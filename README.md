# 🏙️ Berlin Airbnb Market Analysis

## 📌 Project Overview

This end-to-end data analytics project explores the structure, pricing dynamics, and regulatory impact of Berlin's short-term rental market using **Inside Airbnb** data (extracted in **September 2026**). The dataset combines a **cross-sectional snapshot** of active listings, current nightly rates, and minimum-stay rules with **multi-year historical records** covering host onboarding (`host_since`) and review activity (`first_review`, `last_review`).

Berlin enforces strict short-term rental regulations (*Zweckentfremdungsverbot*), requiring municipal permits for tourist stays while exempting residential rentals of 90 days or more. This analysis investigates how geographic location, property type, host scale, and minimum-stay requirements shape nightly pricing and supply distribution across Berlin's 12 administrative districts (*Bezirke*).

### 🎯 Key Business Questions
1. **Geographic Concentration:** Where is Airbnb supply concentrated across Berlin, and which districts command the highest nightly rates?
2. **Property & Room Tiers:** How wide is the pricing gap between entire apartments, hotel rooms, private rooms, and shared rooms?
3. **Regulatory Impact (`Stay Tier`):** How do minimum-night requirements affect nightly pricing between short tourist getaways (`1–3 nights`) and long-term stays (`90+ nights`)?
4. **Host & Market Evolution:** How is supply distributed between individual hosts and multi-listing operators, and what does historical host/review data reveal about market maturity?
5. **Outlier Distortion:** How much do extreme luxury listings (top 1% / p99) skew district-level price benchmarks if left unflagged?

### 🛠️ Tech Stack & Pipeline Architecture
* **Python (`pandas`, `numpy`):** Raw data ingestion, currency string parsing, missing-value handling, feature engineering (`Stay Tier`, `Host Scale Tier`), and percentile-based outlier flagging (`is_high_price_outlier`).
* **MySQL:** Relational schema design, structured data loading, and exploratory SQL analysis (`GROUP BY`, `CASE WHEN`, aggregations, and comparative pricing queries).
* **Tableau:** Interactive 2x2 executive dashboard featuring cross-filtering across geographic maps, district rankings, room-type tiers, and stay-duration segments.

## 🗂️ Repository Structure

```text
berlin-airbnb-market-analysis/
├── README.md
├── python/
│   └── etl_cleaning_and_features.py
├── sql/
│   ├── 01_schema_setup.sql
│   └── 02_exploratory_analysis.sql
└── tableau/
    ├── berlin_airbnb_dashboard.twbx
    └── images/
        ├── dashboard_overview.png
        ├── map_districts.png
        ├── avg_price_district.png
        ├── avg_price_room_type.png
        └── avg_price_stay_tier.png
```
---

## ⚙️ Data Pipeline & Methodology

### 1. Data Ingestion & Cleaning (Python / pandas)
* **Source Data:** Inside Airbnb Berlin dataset (`listings.csv.gz`, September 2026 snapshot), enriched with official Berlin administrative district boundaries (`neighbourhoods.csv` and `neighbourhoods.geojson`).
* **Type Standardization & Parsing:** Converted raw currency strings (`$XXX.XX`) into numeric `FLOAT` values (`nightly_price`), standardized boolean flags (`t`/`f` to `1`/`0`), and parsed historical date fields (`host_since`, `first_review`, `last_review`).
* **Outlier Detection (`is_high_price_outlier`):** Identified extreme luxury listings and data-entry anomalies above the 99th percentile (`p99`). Rather than deleting rows blindly, an explicit binary flag (`is_high_price_outlier`) was engineered so downstream SQL queries and Tableau views can toggle between full-market counts and outlier-filtered price benchmarks (`is_high_price_outlier = 0`).
* **Feature Engineering:**
  * `stay_tier`: Categorized `minimum_nights` into four regulatory brackets: `1-3 nights (Short getaway)`, `4-14 nights (Medium stay)`, `15-89 nights (Extended stay)`, and `90+ nights (Long-term stay)`.
  * `host_scale_tier`: Segmented hosts by portfolio size (`calculated_host_listings_count`) to distinguish individual private hosts from commercial multi-listing operators.

### 2. Relational Modeling & Exploratory Querying (MySQL)
* **Database Design:** Structured the cleaned dataset into a normalized relational schema in MySQL with appropriate data types, primary keys, and indexes on `neighbourhood_group`, `room_type`, and `stay_tier`.
* **Analytical SQL Queries:** Executed multi-dimensional aggregations (`GROUP BY`, conditional `CASE WHEN` metrics, percentile comparisons, and `COUNT(DISTINCT id)` volume checks) to quantify:
  * District-level supply concentration vs. average nightly rates.
  * Pricing gaps across room types and host scale segments.
  * Historical host onboarding cohorts (`YEAR(host_since)`) and review activity trends.

---

## 📊 Interactive Dashboard & Key Findings (Tableau)

<img width="1337" height="943" alt="Captura de pantalla 2026-11-22 a las 10 22 57 p  m" src="https://github.com/user-attachments/assets/fdb32122-c588-4418-82ee-2e8e7b9536ae" />


### Visual Breakdown & Analytical Insights

1. **Geographic Supply & Price Distribution (`Berlin Districts Map`)**
   * **Encoding:** Bubble size represents unique active listings (`COUNTD(id)`), while color intensity encodes average nightly price (`AVG(nightly_price)`).
   * **Finding:** Listing inventory is heavily concentrated in Berlin's central ring—led by **Mitte**, **Friedrichshain-Kreuzberg**, **Pankow**, **Charlottenburg-Wilmersdorf**, and **Neukölln**—while peripheral districts show substantially lower listing density.

2. **District Pricing Benchmark (`Avg Price by District`)**
   * **Encoding:** Ranked horizontal bar chart comparing outlier-adjusted average nightly rates across all 12 administrative districts (*Bezirke*).
   * **Finding:** **Mitte** and **Pankow** lead the market in average nightly pricing (~171–174 EUR), whereas **Reinickendorf** (~92 EUR) represents the most affordable district. Cross-referencing this ranking with the map highlights that higher averages in outer districts like **Spandau** (~156 EUR) are driven by low listing counts rather than high tourist volume.

3. **Accommodation Type Segmentation (`Avg Price by Room Type`)**
   * **Encoding:** Comparative bar chart breaking down average nightly rates across property categories.
   * **Finding:** **Entire home/apt** (~180 EUR) and **Hotel room** (~179 EUR) command nearly double the nightly rate of **Private room** (~98 EUR) and more than four times that of **Shared room** (~43 EUR).

4. **Impact of Minimum Stay Regulations (`Price by Term`)**
   * **Encoding:** Vertical bar chart tracking average nightly price across `stay_tier` duration brackets.
   * **Finding:** Average nightly rates drop by more than **54%** as minimum stay requirements increase—from **179.70 EUR** (`1–3 nights`) and **166.04 EUR** (`4–14 nights`) down to **91.26 EUR** (`15–89 nights`) and **81.37 EUR** (`90+ nights`). This sharp structural drop reflects Berlin's short-term rental law (*Zweckentfremdungsverbot*), which separates high-rate tourist permits from lower-rate medium/long-term residential leases.

### Cross-Filtering & Interactivity
All four views are connected via interactive action filters in Tableau. Clicking any district on the map, room type, or stay tier dynamically filters the remaining three charts, enabling granular drill-downs into local sub-markets (such as comparing long-term vs. short-term pricing specifically inside Neukölln or Mitte).

---

## 🚀 How to Reproduce

1. **Dataset**: Download the Berlin `listings.csv.gz` and `neighbourhoods.csv` files from Inside Airbnb.
2. **ETL Pipeline**: Run `python/etl_cleaning_and_features.py` using Python 3.10+ (`pandas`, `numpy`, `sqlalchemy`, `pymysql`) to clean the raw data, flag `is_high_price_outlier`, load the `airbnb_berlin` database in MySQL, create `vw_airbnb_berlin_bi`, and export the BI dataset.
3. **SQL Analysis**: Run `sql/02_exploratory_analysis.sql` in MySQL against `airbnb_berlin` to reproduce the market, pricing, host scale, and district metrics.
4. **Visualization**: Upload your packaged workbook (`tableau/berlin_airbnb_dashboard.twbx`) or open your local Tableau workbook in Tableau Desktop / Tableau Public to explore the interactive dashboard.
