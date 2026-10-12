# Field Sources

**Project:** Predicting F1 race points from qualifying, weather, and team data

**Sources**
- **Jolpica F1 API** results, qualifying, standings, race calendar, circuits, pit stops
- **Open-Meteo Historical Weather API** hourly weather at circuit coordinates
- **FastF1** track temperature, rainfall, track status
- **Manual Lookup** circuit type, engine suppkier

| Table | Field | Comes From | How | Used For |
| --- | --- | --- | --- | --- |
| `dim_date` | `date_key` | Jolpica F1 API | Taken from the race date and stored as the calendar date key. | Date dimension key for joining races to calendar attributes. |
| `dim_date` | `season_year` | Jolpica F1 API | Extracted from the race season. | Filtering and grouping races by season. |
| `dim_date` | `month` | Derived from race date | Extracted as the calendar month from `date_key`. | Seasonal and month-based analysis. |
| `dim_date` | `day_of_week` | Derived from race date | Calculated from `date_key`. | Comparing race outcomes by day of the week. |
| `dim_date` | `is_weekend` | Derived from race date | Set according to whether `date_key` falls on a Saturday or Sunday. | Weekend-based grouping and analysis. |
| `dim_circuit` | `circuit_id` | Jolpica F1 API | Taken from the circuit identifier. | Primary key for circuits and foreign key from races. |
| `dim_circuit` | `circuit_ref` | Jolpica F1 API | Taken from the circuit reference/slug. | Stable circuit identifier and lookup. |
| `dim_circuit` | `circuit_name` | Jolpica F1 API | Taken from the circuit name. | Identifying and reporting circuit-level results. |
| `dim_circuit` | `locality` | Jolpica F1 API | Taken from the circuit locality. | Circuit location reporting and grouping. |
| `dim_circuit` | `country` | Jolpica F1 API | Taken from the circuit country. | Geographic grouping and reporting. |
| `dim_circuit` | `latitude` | Jolpica F1 API | Taken from the circuit coordinates. | Locating the circuit and matching weather observations. |
| `dim_circuit` | `longitude` | Jolpica F1 API | Taken from the circuit coordinates. | Locating the circuit and matching weather observations. |
| `dim_circuit` | `circuit_type` | Manual Lookup | Assigned from the project’s circuit classification lookup. | Comparing performance across circuit types. |
| `dim_driver` | `driver_id` | Jolpica F1 API | Taken from the driver identifier. | Primary key for drivers and foreign key from race facts. |
| `dim_driver` | `driver_ref` | Jolpica F1 API | Taken from the driver reference/slug. | Stable driver identifier and lookup. |
| `dim_driver` | `driver_code` | Jolpica F1 API | Taken from the driver's short code when available. | Compact driver labels in reports. |
| `dim_driver` | `full_name` | Jolpica F1 API | Combined from the driver's given and family names. | Identifying drivers in reports and analysis. |
| `dim_driver` | `date_of_birth` | Jolpica F1 API | Taken from the driver's date of birth. | Driver profile and age-at-race analysis. |
| `dim_driver` | `nationality` | Jolpica F1 API | Taken from the driver's nationality. | Driver grouping and reporting by nationality. |
| `dim_team` | `team_id` | Jolpica F1 API | Taken from the constructor/team identifier. | Primary key for season-specific teams and fact-table joins. |
| `dim_team` | `team_ref` | Jolpica F1 API | Taken from the constructor reference/slug. | Stable team identifier and lookup. |
| `dim_team` | `team_name` | Jolpica F1 API | Taken from the constructor/team name. | Identifying teams in reports and analysis. |
| `dim_team` | `season_year` | Jolpica F1 API | Extracted from the season in which the team entry applies. | Distinguishing team entries across seasons. |
| `dim_team` | `engine_supplier` | Manual Lookup | Matched to the team and season using the project lookup. | Comparing results by engine supplier. |
| `dim_race` | `race_id` | Jolpica F1 API | Taken from the race identifier. | Primary key for races and foreign key from fact tables. |
| `dim_race` | `season_year` | Jolpica F1 API | Extracted from the race season. | Filtering and grouping races by season. |
| `dim_race` | `round` | Jolpica F1 API | Taken from the race's round number within its season. | Ordering races and identifying the season round. |
| `dim_race` | `circuit_id` | Jolpica F1 API | Taken from the race's circuit reference and matched to `dim_circuit`. | Linking a race to its circuit. |
| `dim_race` | `race_name` | Jolpica F1 API | Taken from the race name. | Identifying races in reports. |
| `dim_race` | `race_date` | Jolpica F1 API | Taken from the scheduled race date. | Race calendar and date-based analysis. |
| `dim_race` | `race_start_time` | Jolpica F1 API | Combined from the scheduled race date and start time when available. | Time-aware joins and matching weather to the race. |
| `fact_race_result` | `race_id` | Jolpica F1 API | Linked to the corresponding race in `dim_race`. | Identifies the race for each result. |
| `fact_race_result` | `driver_id` | Jolpica F1 API | Linked to the corresponding driver in `dim_driver`. | Identifies the driver for each result. |
| `fact_race_result` | `team_id` | Jolpica F1 API | Linked to the driver's constructor/team entry in `dim_team`. | Identifies the team for each result. |
| `fact_race_result` | `grid_position` | Jolpica F1 API | Taken from the driver's starting grid position. | Predictor describing starting position. |
| `fact_race_result` | `finishing_position` | Jolpica F1 API | Taken from the final classification position. | Race outcome and model target context. |
| `fact_race_result` | `points` | Jolpica F1 API | Taken from the points awarded for the race result. | Main race-points outcome to predict and analyze. |
| `fact_race_result` | `fastest_lap_time` | Jolpica F1 API | Taken from the recorded fastest-lap time and stored as an interval. | Race-performance analysis and potential predictor. |
| `fact_race_result` | `result_id` | Jolpica F1 API | Taken from the result record identifier. | Primary key for a race-result record. |
| `fact_race_result` | `is_dnf` | Derived from Jolpica F1 API | Set from the result status/classification indicating the driver did not finish. | Distinguishing finishers from non-finishers in analysis. |
| `fact_qualifying` | `race_id` | Jolpica F1 API | Linked to the corresponding race in `dim_race`. | Identifies the race for each qualifying result. |
| `fact_qualifying` | `driver_id` | Jolpica F1 API | Linked to the corresponding driver in `dim_driver`. | Identifies the driver for each qualifying result. |
| `fact_qualifying` | `team_id` | Jolpica F1 API | Linked to the driver's constructor/team entry in `dim_team`. | Identifies the team for each qualifying result. |
| `fact_qualifying` | `qualifying_position` | Jolpica F1 API | Taken from the final qualifying position. | Predictor describing the driver's qualifying rank. |
| `fact_qualifying` | `qualifying_time` | Jolpica F1 API | Taken from the recorded qualifying time and stored as an interval. | Qualifying-performance analysis. |
| `fact_qualifying` | `q1_time` | Jolpica F1 API | Taken from the driver's Q1 time, where available. | Qualifying-performance predictor. |
| `fact_qualifying` | `q2_time` | Jolpica F1 API | Taken from the driver's Q2 time, where available. | Qualifying-performance predictor. |
| `fact_qualifying` | `q3_time` | Jolpica F1 API | Taken from the driver's Q3 time, where available. | Qualifying-performance predictor. |
| `fact_qualifying` | `best_time` | Derived from Jolpica F1 API | Selected as the driver's best available qualifying session time. | Comparing qualifying pace across drivers. |
| `fact_qualifying` | `gap_to_pole` | Derived from Jolpica F1 API | Calculated as the driver's best time minus the pole time for the session. | Measuring qualifying pace relative to pole. |
| `fact_qualifying` | `result_id` | Jolpica F1 API | Taken from the qualifying result record identifier. | Primary key for a qualifying record. |
| `fact_driver_standing` | `standing_id` | Jolpica F1 API | Taken from the driver-standing record identifier. | Primary key for a standing record. |
| `fact_driver_standing` | `race_id` | Jolpica F1 API | Linked to the race after which the standing is recorded. | Identifies the update point for championship standings. |
| `fact_driver_standing` | `driver_id` | Jolpica F1 API | Linked to the corresponding driver in `dim_driver`. | Identifies the driver in the standings. |
| `fact_driver_standing` | `team_id` | Jolpica F1 API | Linked to the driver's constructor/team entry in `dim_team`. | Identifies the team in the standings. |
| `fact_driver_standing` | `position_after` | Jolpica F1 API | Taken from the driver's championship position after the race. | Tracking championship position over a season. |
| `fact_driver_standing` | `points_after` | Jolpica F1 API | Taken from the driver's accumulated points after the race. | Tracking championship points over a season. |
| `fact_driver_standing` | `wins_after` | Jolpica F1 API | Taken from the driver's accumulated wins after the race. | Tracking championship wins over a season. |
| `fact_weather` | `weather_id` | Generated during loading | Assigned as the unique identifier for the weather record. | Primary key for a weather record. |
| `fact_weather` | `race_id` | Jolpica F1 API | Linked to the race whose weather is summarized. | Associates weather with a race. |
| `fact_weather` | `temperature` | Open-Meteo Historical Weather API | Retrieved for the circuit coordinates and race time; summarized for the race. | Weather predictor for race-points analysis. |
| `fact_weather` | `humidity` | Open-Meteo Historical Weather API | Retrieved for the circuit coordinates and race time; summarized for the race. | Weather predictor for race-points analysis. |
| `fact_weather` | `wind_speed` | Open-Meteo Historical Weather API | Retrieved for the circuit coordinates and race time; summarized for the race. | Weather predictor for race-points analysis. |
| `fact_weather` | `precipitation` | Open-Meteo Historical Weather API; FastF1 | Open-Meteo precipitation is matched to the race time; FastF1 rainfall/track observations can provide a cross-check. | Wet-weather predictor for race-points analysis. |
| `fact_weather` | `weather_condition` | Open-Meteo Historical Weather API | Retrieved or categorized from the weather condition at the circuit around race time. | Describing and grouping race weather conditions. |
| `fact_race_control` | `pit_stop_id` | Jolpica F1 API | Taken from the pit-stop record identifier. | Primary key for a pit-stop record. |
| `fact_race_control` | `race_id` | Jolpica F1 API | Linked to the corresponding race in `dim_race`. | Identifies the race for each pit stop. |
| `fact_race_control` | `team_id` | Jolpica F1 API | Linked to the driver's constructor/team entry in `dim_team`. | Identifies the team for each pit stop. |
| `fact_race_control` | `driver_id` | Jolpica F1 API | Linked to the corresponding driver in `dim_driver`. | Identifies the driver for each pit stop. |
| `fact_race_control` | `pit_stop_time` | Jolpica F1 API | Taken from the recorded pit-stop duration and stored as an interval. | Pit-stop strategy and race-performance analysis. |