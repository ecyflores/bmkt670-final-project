-- schema.sql | F1 race outcome prediction | PostgreSQL
-- Prediction unit: one driver in one race. Target: points scored.
-- Safe to re-run: drops everything first (view, facts, then dims).
-- =====================================================================
 
DROP VIEW  IF EXISTS ml_features_race_outcome CASCADE;
DROP TABLE IF EXISTS fact_race_control    CASCADE;
DROP TABLE IF EXISTS fact_stint           CASCADE;
DROP TABLE IF EXISTS fact_pit_stop        CASCADE;
DROP TABLE IF EXISTS fact_weather         CASCADE;
DROP TABLE IF EXISTS fact_driver_standing CASCADE;
DROP TABLE IF EXISTS fact_qualifying      CASCADE;
DROP TABLE IF EXISTS fact_race_result     CASCADE;
DROP TABLE IF EXISTS dim_race             CASCADE;
DROP TABLE IF EXISTS dim_team             CASCADE;
DROP TABLE IF EXISTS dim_driver           CASCADE;
DROP TABLE IF EXISTS dim_circuit          CASCADE;
DROP TABLE IF EXISTS dim_date             CASCADE;
 

-- dimension tables

CREATE TABLE dim_date(
    date_key DATE PRIMARY KEY,
    season_year INT NOT NULL,
    month INT NOT NULL,
    day_of_week TEXT NOT NULL,
    is_weekend BOOLEAN NOT NULL
);

CREATE TABLE dim_circuit(
    circuit_id INT PRIMARY KEY,
    circuit_ref TEXT UNIQUE NOT NULL,
    circuit_name TEXT NOT NULL,
    locality TEXT,
    country TEXT NOT NULL,
    latitude NUMERIC(9,6) NOT NULL,
    longitude NUMERIC(9,6) NOT NULL,
    circuit_type TEXT NOT NULL
);

CREATE TABLE dim_driver(
    driver_id INT PRIMARY KEY,
    driver_ref TEXT UNIQUE NOT NULL,
    driver_code TEXT,
    full_name TEXT NOT NULL,
    date_of_birth DATE NOT NULL,
    nationality TEXT NOT NULL
);

CREATE TABLE dim_team(
    team_id INT PRIMARY KEY,
    team_ref TEXT UNIQUE NOT NULL,
    team_name TEXT NOT NULL,
    season_year INT NOT NULL,
    engine_supplier TEXT NOT NULL,
    UNIQUE (team_ref, season_year)
);

CREATE TABLE dim_race(
    race_id INT PRIMARY KEY,
    season_year INT NOT NULL,
    round INT NOT NULL,
    circuit_id INT NOT NULL,
    race_name TEXT NOT NULL,
    race_date DATE NOT NULL,
    race_start_time TIMESTAMP,
    FOREIGN KEY (circuit_id) REFERENCES dim_circuit(circuit_id)
);


-- fact tables 

CREATE TABLE fact_race_result(
    race_id INT NOT NULL,
    driver_id INT NOT NULL,
    team_id INT NOT NULL,
    grid_position INT NOT NULL,
    finishing_position INT NOT NULL,
    points NUMERIC(5,2) NOT NULL,
    fastest_lap_time INTERVAL,
    result_id INT PRIMARY KEY,
    is_dnf BOOLEAN NOT NULL,
    UNIQUE (race_id, driver_id),
    FOREIGN KEY (race_id) REFERENCES dim_race(race_id),
    FOREIGN KEY (driver_id) REFERENCES dim_driver(driver_id),
    FOREIGN KEY (team_id) REFERENCES dim_team(team_id)
);

CREATE TABLE fact_qualifying(
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
);

CREATE TABLE fact_driver_standing(
    standing_id INT PRIMARY KEY,
    race_id INT NOT NULL,
    driver_id INT NOT NULL,
    team_id INT NOT NULL,
    position_after INT NOT NULL,
    points_after NUMERIC(5,2) NOT NULL,
    wins_after INT NOT NULL,
    UNIQUE (race_id, driver_id),
    FOREIGN KEY (race_id) REFERENCES dim_race(race_id),
    FOREIGN KEY (driver_id) REFERENCES dim_driver(driver_id),
    FOREIGN KEY (team_id) REFERENCES dim_team(team_id)
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

CREATE TABLE fact_race_control(
    pit_stop_id INT PRIMARY KEY,
    race_id INT NOT NULL,
    team_id INT NOT NULL,
    driver_id INT NOT NULL,
    pit_stop_time INTERVAL,
    UNIQUE (race_id, team_id, driver_id),
    FOREIGN KEY (race_id) REFERENCES dim_race(race_id),
    FOREIGN KEY (team_id) REFERENCES dim_team(team_id),
    FOREIGN KEY (driver_id) REFERENCES dim_driver(driver_id)
);
