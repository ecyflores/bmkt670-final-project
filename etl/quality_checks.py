"""Run post-load data quality checks against PostgreSQL and source CSVs."""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Any

import psycopg2
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLEAN_DIR = PROJECT_ROOT / "data" / "clean"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
TABLES = (
    "dim_circuit",
    "dim_driver",
    "dim_race",
    "fact_race_result",
    "fact_driver_standing",
    "fact_weather",
    "ml_features_race_outcome",
)
CORE_FEATURE_MISSINGNESS_LIMIT = 0.05
WEATHER_WINDOW_BEFORE_RACE_DAYS = 3
WEATHER_WINDOW_AFTER_RACE_DAYS = 2


def _csv_row_count(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.reader(csv_file)
        next(reader, None)
        return sum(1 for _ in reader)


def _one_csv(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"Expected one file matching {pattern!r} in {directory}; "
            f"found {len(matches)}."
        )
    return matches[0]


def _print_check(label: str, number: int | float, passed: bool, rule: str) -> bool:
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {label}: {number} (rule: {rule})")
    return passed


def _run_zero_check(cursor: Any, label: str, query: str, rule: str = "0") -> bool:
    cursor.execute(query)
    count = int(cursor.fetchone()[0])
    return _print_check(label, count, count == 0, rule)


def _check_row_counts(cursor: Any) -> list[bool]:
    results = []
    for table_name in TABLES:
        clean_path = CLEAN_DIR / f"{table_name}.csv"
        expected_rows = _csv_row_count(clean_path)
        cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
        loaded_rows = int(cursor.fetchone()[0])
        difference = loaded_rows - expected_rows
        results.append(
            _print_check(
                f"{table_name} row-count difference (loaded - clean CSV)",
                difference,
                difference == 0,
                f"0; clean CSV has {expected_rows} rows",
            )
        )
    return results


def _check_raw_result_reconciliation(cursor: Any) -> bool:
    raw_results_path = _one_csv(
        RAW_DIR,
        "f1_*all_race_sprint_results.csv",
    )
    with raw_results_path.open("r", encoding="utf-8-sig", newline="") as raw_file:
        main_race_rows = sum(
            row.get("race_type", "").strip().lower() == "main_race"
            for row in csv.DictReader(raw_file)
        )
    cursor.execute("SELECT COUNT(*) FROM fact_race_result")
    loaded_rows = int(cursor.fetchone()[0])
    difference = loaded_rows - main_race_rows
    return _print_check(
        "fact_race_result reconciliation (loaded - raw main-race rows)",
        difference,
        difference == 0,
        f"0; sprint rows are excluded from fact_race_result "
        f"({main_race_rows} raw main-race rows)",
    )


def _check_weather_timestamps(cursor: Any) -> bool:
    """Allow UTC-converted weekend timestamps a broad timezone-safe race window."""
    from datetime import timedelta

    import pandas as pd

    weather_path = _one_csv(RAW_DIR, "f1_weather_*.csv")
    races_path = CLEAN_DIR / "dim_race.csv"
    races = pd.read_csv(races_path, usecols=["season_year", "round", "race_date"])
    weather = pd.read_csv(
        weather_path,
        usecols=["season", "round", "time_utc"],
    )
    races["season_year"] = pd.to_numeric(races["season_year"], errors="coerce")
    races["round"] = pd.to_numeric(races["round"], errors="coerce")
    weather["season"] = pd.to_numeric(weather["season"], errors="coerce")
    weather["round"] = pd.to_numeric(weather["round"], errors="coerce")
    weather["time_utc"] = pd.to_datetime(weather["time_utc"], utc=True, errors="coerce")
    race_lookup = races.set_index(["season_year", "round"])["race_date"]
    outside_window = 0
    invalid_timestamp = 0
    for row in weather.itertuples(index=False):
        if pd.isna(row.time_utc):
            invalid_timestamp += 1
            continue
        key = (row.season, row.round)
        if key not in race_lookup.index:
            continue
        race_date = pd.Timestamp(race_lookup.loc[key]).tz_localize("UTC")
        earliest = race_date - timedelta(days=WEATHER_WINDOW_BEFORE_RACE_DAYS)
        latest = race_date + timedelta(days=WEATHER_WINDOW_AFTER_RACE_DAYS)
        if not earliest <= row.time_utc <= latest:
            outside_window += 1
    passed = outside_window == 0 and invalid_timestamp == 0
    number = outside_window + invalid_timestamp
    return _print_check(
        "Matched weather timestamps outside race-weekend window",
        number,
        passed,
        f"0; valid UTC timestamps within race date -"
        f"{WEATHER_WINDOW_BEFORE_RACE_DAYS} days to +{WEATHER_WINDOW_AFTER_RACE_DAYS} day",
    )


def _check_unmatched_weather_races() -> bool:
    import pandas as pd

    races_path = CLEAN_DIR / "dim_race.csv"
    weather_path = _one_csv(RAW_DIR, "f1_weather_*.csv")
    races = pd.read_csv(races_path, usecols=["season_year", "round"])
    weather = pd.read_csv(weather_path, usecols=["season", "round"])
    race_keys = set(
        map(
            tuple,
            races[["season_year", "round"]]
            .apply(pd.to_numeric, errors="coerce")
            .dropna()
            .astype(int)
            .drop_duplicates()
            .to_numpy(),
        )
    )
    weather_keys = (
        weather[["season", "round"]]
        .apply(pd.to_numeric, errors="coerce")
        .dropna()
        .astype(int)
    )
    unmatched_count = sum(
        (int(season), int(round_number)) not in race_keys
        for season, round_number in weather_keys.itertuples(index=False, name=None)
    )
    return _print_check(
        "Hourly weather rows without a matching clean race",
        unmatched_count,
        unmatched_count == 0,
        "0; each weather season/round must exist in dim_race",
    )


def _check_core_feature_missingness(cursor: Any) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) FILTER (
            WHERE target_points IS NULL
               OR grid_position IS NULL
               OR driver_points_before_race IS NULL
               OR driver_avg_points_last_3_before_race IS NULL
               OR driver_starts_before_race IS NULL
               OR split IS NULL
        ), COUNT(*)
        FROM ml_features_race_outcome
        """
    )
    missing_rows, total_rows = cursor.fetchone()
    if not total_rows:
        return _print_check(
            "Core ML feature missingness",
            100.0,
            False,
            f"under {CORE_FEATURE_MISSINGNESS_LIMIT:.0%}; table must not be empty",
        )
    missing_percent = 100 * int(missing_rows) / int(total_rows)
    passed = missing_percent < CORE_FEATURE_MISSINGNESS_LIMIT * 100
    return _print_check(
        "Core ML feature missingness (%)",
        round(missing_percent, 2),
        passed,
        f"percent under {CORE_FEATURE_MISSINGNESS_LIMIT:.0%} "
        f"({missing_rows}/{total_rows} rows)",
    )


def run_checks(cursor: Any) -> list[bool]:
    checks = [
        _run_zero_check(
            cursor,
            "Duplicate driver-race results",
            """
            SELECT COUNT(*) - COUNT(DISTINCT (race_id, driver_id))
            FROM fact_race_result
            """,
            "0; one result per driver per race",
        ),
        _run_zero_check(
            cursor,
            "Duplicate ML feature rows",
            """
            SELECT COUNT(*) - COUNT(DISTINCT (race_id, driver_id))
            FROM ml_features_race_outcome
            """,
            "0; one feature row per driver per race",
        ),
        _run_zero_check(
            cursor,
            "Out-of-range numeric values",
            """
            SELECT
                (SELECT COUNT(*) FROM fact_race_result
                 WHERE points < 0 OR points > 26
                    OR grid_position < 1 OR grid_position > 22)
              + (SELECT COUNT(*) FROM ml_features_race_outcome
                 WHERE target_points < 0 OR target_points > 26
                    OR grid_position < 1 OR grid_position > 22
                    OR driver_points_before_race < 0
                    OR driver_avg_points_last_3_before_race < 0
                    OR driver_starts_before_race < 0)
            """,
            "0; points 0-26, grid 1-22, prior-history features nonnegative",
        ),
        _run_zero_check(
            cursor,
            "Orphaned foreign keys",
            """
            SELECT
                (SELECT COUNT(*) FROM dim_race r
                 LEFT JOIN dim_circuit c ON c.circuit_id = r.circuit_id
                 WHERE c.circuit_id IS NULL)
              + (SELECT COUNT(*) FROM fact_race_result f
                 LEFT JOIN dim_race r ON r.race_id = f.race_id
                 LEFT JOIN dim_driver d ON d.driver_id = f.driver_id
                 WHERE r.race_id IS NULL OR d.driver_id IS NULL)
              + (SELECT COUNT(*) FROM fact_driver_standing f
                 LEFT JOIN dim_race r ON r.race_id = f.race_id
                 LEFT JOIN dim_driver d ON d.driver_id = f.driver_id
                 WHERE r.race_id IS NULL OR d.driver_id IS NULL)
              + (SELECT COUNT(*) FROM fact_weather f
                 LEFT JOIN dim_race r ON r.race_id = f.race_id
                 WHERE r.race_id IS NULL)
              + (SELECT COUNT(*) FROM ml_features_race_outcome f
                 LEFT JOIN dim_race r ON r.race_id = f.race_id
                 LEFT JOIN dim_driver d ON d.driver_id = f.driver_id
                 WHERE r.race_id IS NULL OR d.driver_id IS NULL)
            """,
        ),
        _check_core_feature_missingness(cursor),
        _run_zero_check(
            cursor,
            "Invalid month one-hot rows",
            """
            SELECT COUNT(*)
            FROM ml_features_race_outcome
            WHERE (
                race_month_01::int + race_month_02::int
              + race_month_03::int + race_month_04::int
              + race_month_05::int + race_month_06::int
              + race_month_07::int + race_month_08::int
              + race_month_09::int + race_month_10::int
              + race_month_11::int + race_month_12::int
            ) <> 1
            """,
        ),
        _run_zero_check(
            cursor,
            "Season/split mismatches",
            """
            SELECT COUNT(*)
            FROM ml_features_race_outcome
            WHERE (season_year BETWEEN 2021 AND 2023 AND split <> 'train')
               OR (season_year = 2024 AND split <> 'validate')
               OR (season_year = 2025 AND split <> 'test')
               OR season_year NOT BETWEEN 2021 AND 2025
            """,
        ),
    ]
    checks.extend(_check_row_counts(cursor))
    checks.append(_check_raw_result_reconciliation(cursor))
    checks.append(_check_weather_timestamps(cursor))
    checks.append(_check_unmatched_weather_races())
    return checks


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    required_settings = ("PGDATABASE", "PGUSER", "PGPASSWORD")
    missing = [name for name in required_settings if not os.getenv(name)]
    if missing:
        raise SystemExit(
            "Missing database settings in environment or .env: "
            f"{', '.join(missing)}"
        )

    connection = psycopg2.connect(
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
    )
    try:
        with connection:
            with connection.cursor() as cursor:
                results = run_checks(cursor)
    finally:
        connection.close()

    failures = len(results) - sum(results)
    print(f"\nQuality checks: {len(results) - failures} passed, {failures} failed.")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()