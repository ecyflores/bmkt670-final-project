# bmkt670-final-project
Final Project for BMKT 670
# Getting Closer to the Championship 

## Business Question
How many points will top 5 championship contenders score in the upcoming race?

## Target Variable
Points scored or classification style (podium, points, no points)

## Prediction Unit
One row in my ML feature table = one race or lap

## Data Sources
| Source | What it provides | Access |
|Jolpica F1 API|Historical race data – qualifying times, driver standings, circuit metadata|Free API|  
|Open-Metro Weather API|Hourly weather at circuits on race weekend – temp, precipitation, wind|Free API|  
|FastF1 Python|Tire data, pit stop counts w/duration, car performance metric|Python Package|  

[For hand-downloaded files, list the URL, date downloaded, and the clicks or filters you used.]

## How to Run
1. Create and activate a virtual environment
2. Install packages: pip install -r requirements.txt
3. Create a .env file with your API keys and DB_PASSWORD 
4. Pull the data: run each script in etl/ (e.g., python etl/extract_games.py)  
5. Build the database: run sql/schema.sql in pgAdmin or psql
6. Confirm it worked: python db_check.py (should print all table names)


## AI Usage
[Which AI tools you used and for which parts]