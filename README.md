# bmkt670-final-project
Final Project for BMKT 670
# Getting Closer to the Championship 

## Business Question
How many points will top 5 championship contenders score in the upcoming race?

## Target Variable
Points scored or classification style (podium, points, no points)

## Prediction Unit
One row in `ml_features_race_outcome` = one driver in one main race. The target
is that driver's points from the race.

## Data Sources
| Source | What it provides | Access |
|Jolpica F1 API|Historical race data – qualifying times, driver standings, circuit metadata|Free API|  
|Open-Metro Weather API|Hourly weather at circuits on race weekend – temp, precipitation, wind|Free API|  
|FastF1 Python|Tire data, pit stop counts w/duration, car performance metric|Python Package|  


## How to Run
1. Create and activate a virtual environment
2. Install the database dependencies: `pip install psycopg2-binary python-dotenv`
3. Create a `.env` file with `PGDATABASE`, `PGUSER`, `PGPASSWORD`, and optionally `PGHOST` and `PGPORT`. Do not commit this file or put passwords in source code.
4. Run the full pipeline from the repository root: `python run_pipeline.py`. It extracts race and weather data into `data/raw/`, transforms the CSVs into `data/clean/`, recreates the database schema, loads the tables, and runs quality checks. It stops on extraction, transform, schema, or load errors. Quality-check failures are reported after the pipeline steps finish and cause the command to exit with a failure status.
5. Review the clean CSVs before loading if desired. Race results are one row per driver per main race; sprint result rows are excluded from that table. Driver standings include main-race and sprint points. Weather is summarized per race by averaging temperature, humidity, and wind speed, summing precipitation, and using the most frequent weather code across weekend hours. Weather timestamps are parsed as UTC and races/weather are joined using season and round; unmatched weather keys are reported by quality checks. The transform also writes `ml_features_race_outcome.csv`, using only earlier main-race results for rolling/cumulative features, one-hot encodes scheduled race month, identifies sprint weekends, and sets splits to 2021–2023 train, 2024 validate, and 2025 test. Weekend-aggregated weather is not used as a model feature because it may include observations after race start.



## AI Usage
Claude 
    for picking and choosing which fields to pull from APIs
    data flow png
    honing in on error from schema
Copilot in Visual Studio
    for editing the extract files to pull data from seasons 2021-2025
    getting the load file to correctly loop through
    helped build quality checks out further to fully get through everything in the data
