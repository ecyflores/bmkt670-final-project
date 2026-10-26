# bmkt670-final-project
Final Project for BMKT 670
# Getting Closer to the Championship 

## Business Question
How many points will top 5 championship contenders score in the upcoming race?

## Target Variable
Points scored or classification style (podium, points, no points)

## Prediction Unit
One row in my ML feature table = one race

## Data Sources
| Source | What it provides | Access |
|Jolpica F1 API|Historical race data – qualifying times, driver standings, circuit metadata|Free API|  
|Open-Metro Weather API|Hourly weather at circuits on race weekend – temp, precipitation, wind|Free API|  
|FastF1 Python|Tire data, pit stop counts w/duration, car performance metric|Python Package|  


## How to Run
1. Create and activate a virtual environment
2. Install the database-check dependencies: `pip install psycopg2-binary python-dotenv`
3. Create a .env file with your API keys and `DB_NAME`, `DB_USER`, and `DB_PASSWORD` (optionally `DB_HOST` and `DB_PORT`).
4. Pull the raw data by running the extractors in `etl/`.
5. Transform the raw CSVs into schema-shaped tables: `python etl/transform.py`. This writes `data/clean/<table_name>.csv` and leaves `data/raw/` unchanged. Race results are one row per driver per main race; sprint result rows are excluded from that prediction table. Driver standings are calculated from all race and sprint points before filtering to main-race results. Weather is summarized per race by averaging temperature, humidity, and wind speed, summing precipitation, and using the most frequent weather code across the available weekend hours. Weather timestamps are parsed as UTC and races/weather are joined using season and round. The script reports any raw weather rows that do not have a matching race key and excludes them from `fact_weather`.
6. Review the clean CSVs, then build and check the database with `python db_check.py` (executes `schema.sql` from the project root; run it against an empty database).



## AI Usage
Claude 
    for picking and choosing which fields to pull from APIs
    data flow png
    honing in on error from schema
Copilot in Visual Studio
    for editing the extract files to pull data from seasons 2021-2025
