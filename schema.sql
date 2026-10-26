-- schema.sql | F1 race outcome prediction | PostgreSQL
-- Prediction unit: one driver in one race. Target: points scored.
-- Safe to re-run: drops the feature table, facts, then dimensions first.
-- =====================================================================
 

DROP TABLE IF EXISTS ml_features_race_outcome CASCADE;
DROP TABLE IF EXISTS fact_weather         CASCADE;
DROP TABLE IF EXISTS fact_driver_standing CASCADE;
DROP TABLE IF EXISTS fact_race_result     CASCADE;
DROP TABLE IF EXISTS dim_race             CASCADE;
DROP TABLE IF EXISTS dim_driver           CASCADE;
DROP TABLE IF EXISTS dim_circuit          CASCADE;

-- dimension tables


CREATE TABLE dim_circuit(
    circuit_id INT PRIMARY KEY,
    circuit_ref TEXT UNIQUE NOT NULL,
    circuit_name TEXT NOT NULL,
    locality TEXT,
    country TEXT,
    latitude NUMERIC(9,6) NOT NULL,
    longitude NUMERIC(9,6) NOT NULL
);

CREATE TABLE dim_driver(
    driver_id INT PRIMARY KEY,
    driver_ref TEXT UNIQUE NOT NULL,
    driver_code TEXT,
    full_name TEXT NOT NULL,
    date_of_birth DATE,
    nationality TEXT
);

CREATE TABLE dim_race(
    race_id INT PRIMARY KEY,
    season_year INT NOT NULL,
    round INT NOT NULL,
    circuit_id INT NOT NULL,
    race_name TEXT NOT NULL,
    race_date DATE NOT NULL,
    FOREIGN KEY (circuit_id) REFERENCES dim_circuit(circuit_id)
);


-- fact tables 

CREATE TABLE fact_race_result(
    race_id INT NOT NULL,
    driver_id INT NOT NULL,
    grid_position INT NOT NULL,
    finishing_position INT NOT NULL,
    points NUMERIC(5,2) NOT NULL,
    fastest_lap_time INTERVAL,
    result_id INT PRIMARY KEY,
    is_dnf BOOLEAN NOT NULL,
    UNIQUE (race_id, driver_id),
    FOREIGN KEY (race_id) REFERENCES dim_race(race_id),
    FOREIGN KEY (driver_id) REFERENCES dim_driver(driver_id)
);

CREATE TABLE fact_driver_standing(
    standing_id INT PRIMARY KEY,
    race_id INT NOT NULL,
    driver_id INT NOT NULL,
    position_after INT NOT NULL,
    points_after NUMERIC(5,2) NOT NULL,
    wins_after INT NOT NULL,
    UNIQUE (race_id, driver_id),
    FOREIGN KEY (race_id) REFERENCES dim_race(race_id),
    FOREIGN KEY (driver_id) REFERENCES dim_driver(driver_id)
);

CREATE TABLE fact_weather(
    weather_id INT PRIMARY KEY,
    race_id INT NOT NULL,
    temperature NUMERIC(5,2),
    humidity NUMERIC(5,2),
    wind_speed NUMERIC(5,2),
    precipitation NUMERIC(5,2),
    weather_condition TEXT,
    UNIQUE (race_id),
    FOREIGN KEY (race_id) REFERENCES dim_race(race_id)
);

-- ML Feature Table

CREATE TABLE ml_features_race_outcome(
    feature_id INT PRIMARY KEY,
    race_id INT NOT NULL,
    driver_id INT NOT NULL,
    season_year INT NOT NULL,
    round INT NOT NULL,
    target_points NUMERIC(5,2) NOT NULL,
    grid_position INT NOT NULL,
    driver_points_before_race NUMERIC(7,2) NOT NULL,
    driver_avg_points_last_3_before_race NUMERIC(5,2) NOT NULL,
    driver_starts_before_race INT NOT NULL,
    sprint_weekend BOOLEAN NOT NULL,
    race_month_01 BOOLEAN NOT NULL,
    race_month_02 BOOLEAN NOT NULL,
    race_month_03 BOOLEAN NOT NULL,
    race_month_04 BOOLEAN NOT NULL,
    race_month_05 BOOLEAN NOT NULL,
    race_month_06 BOOLEAN NOT NULL,
    race_month_07 BOOLEAN NOT NULL,
    race_month_08 BOOLEAN NOT NULL,
    race_month_09 BOOLEAN NOT NULL,
    race_month_10 BOOLEAN NOT NULL,
    race_month_11 BOOLEAN NOT NULL,
    race_month_12 BOOLEAN NOT NULL,
    split TEXT NOT NULL CHECK (split IN ('train', 'validate', 'test')),
    UNIQUE (race_id, driver_id),
    FOREIGN KEY (race_id) REFERENCES dim_race(race_id),
    FOREIGN KEY (driver_id) REFERENCES dim_driver(driver_id)
);

-- Everything below is no longer needed

-- DROP TABLE IF EXISTS dim_team             CASCADE;
-- DROP TABLE IF EXISTS dim_date             CASCADE;
-- DROP TABLE IF EXISTS fact_qualifying      CASCADE;
-- DROP TABLE IF EXISTS fact_race_control    CASCADE;
-- DROP TABLE IF EXISTS fact_stint           CASCADE;
-- DROP TABLE IF EXISTS fact_pit_stop        CASCADE;

-- I have decided to not use the date table for the prediction model, but I will keep it here for future reference.
/* CREATE TABLE dim_date(
    date_key DATE PRIMARY KEY,
    season_year INT NOT NULL,
    month INT NOT NULL,
    day_of_week TEXT NOT NULL,
    is_weekend BOOLEAN NOT NULL
); */ 

-- I have decided not to use the team table for the prediction model, but I will keep it here for future reference.
/* CREATE TABLE dim_team(
    team_id INT PRIMARY KEY,
    team_ref TEXT UNIQUE NOT NULL,
    team_name TEXT NOT NULL,
    season_year INT NOT NULL,
    engine_supplier TEXT NOT NULL,
    UNIQUE (team_ref, season_year)
); */ 


-- After evalutaing the qualifying 
/* CREATE TABLE fact_qualifying(
    race_id INT NOT NULL,
    driver_id INT NOT NULL,
    team_id INT NOT NULL,
    qualifying_position INT NOT NULL,
    qualifying_time INTERVAL,
    q1_time NUMERIC(7,3),
    q2_time NUMERIC(7,3),
    q3_time NUMERIC(7,3),
    best_time NUMERIC(7,3),
    gap_to_pole NUMERIC(6,3),
    result_id INT PRIMARY KEY,
    UNIQUE (race_id, driver_id),
    FOREIGN KEY (race_id) REFERENCES dim_race(race_id),
    FOREIGN KEY (driver_id) REFERENCES dim_driver(driver_id),
    FOREIGN KEY (team_id) REFERENCES dim_team(team_id)
); */


-- After evaluating the race control table I have decided not to use it for the prediction model, but I will keep it here for future reference.
/* CREATE TABLE fact_race_control(
    pit_stop_id INT PRIMARY KEY,
    race_id INT NOT NULL,
    team_id INT NOT NULL,
    driver_id INT NOT NULL,
    pit_stop_time INTERVAL,
    UNIQUE (race_id, team_id, driver_id),
    FOREIGN KEY (race_id) REFERENCES dim_race(race_id),
    FOREIGN KEY (team_id) REFERENCES dim_team(team_id),
    FOREIGN KEY (driver_id) REFERENCES dim_driver(driver_id)
); */ 
