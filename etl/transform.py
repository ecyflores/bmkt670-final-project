"""Transform the raw F1 race and weather extracts into schema-shaped CSVs."""

from __future__ import annotations

import re
import warnings
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
MANUAL_DIR = PROJECT_ROOT / "data" / "manual"
CLEAN_DIR = PROJECT_ROOT / "data" / "clean"

TABLE_COLUMNS = {
    "dim_circuit": [
        "circuit_id",
        "circuit_ref",
        "circuit_name",
        "locality",
        "country",
        "latitude",
        "longitude",
    ],
    "dim_driver": [
        "driver_id",
        "driver_ref",
        "driver_code",
        "full_name",
        "date_of_birth",
        "nationality",
    ],
    "dim_race": [
        "race_id",
        "season_year",
        "round",
        "circuit_id",
        "race_name",
        "race_date",
    ],
    "fact_race_result": [
        "race_id",
        "driver_id",
        "team_id",
        "grid_position",
        "finishing_position",
        "points",
        "fastest_lap_time",
        "result_id",
        "is_dnf",
    ],
    "fact_driver_standing": [
        "standing_id",
        "race_id",
        "driver_id",
        "team_id",
        "position_after",
        "points_after",
        "wins_after",
    ],
    "fact_weather": [
        "weather_id",
        "race_id",
        "temperature",
        "humidity",
        "wind_speed",
        "precipitation",
        "weather_condition",
    ],
    "ml_features_race_outcome": [
        "feature_id",
        "race_id",
        "driver_id",
        "season_year",
        "round",
        "target_points",
        "grid_position",
        "driver_points_before_race",
        "driver_avg_points_last_3_before_race",
        "driver_starts_before_race",
        "sprint_weekend",
        *[f"race_month_{month:02d}" for month in range(1, 13)],
        "split",
    ],
}

RAW_RACE_PATTERN = "f1_*all_race_sprint_results.csv"
RAW_WEATHER_PATTERN = "f1_weather_*.csv"


def _one_file(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"Expected exactly one file matching {pattern!r} in {directory}; "
            f"found {len(matches)}."
        )
    return matches[0]


def _slug(value: Any) -> str:
    value = str(value).strip().lower()
    return re.sub(r"[^a-z0-9]+", "_", value).strip("_")


def _read_manual_lookup(filename: str, key_column: str) -> dict[str, dict[str, Any]]:
    path = MANUAL_DIR / filename
    if not path.exists():
        return {}

    lookup = pd.read_csv(path, dtype=str).fillna("")
    if key_column not in lookup.columns:
        raise ValueError(f"{path} must contain a {key_column!r} column.")
    keys = lookup[key_column].map(_slug)
    if keys.duplicated().any():
        duplicates = sorted(keys[keys.duplicated(keep=False)].unique())
        raise ValueError(f"{path} contains duplicate {key_column} values: {duplicates}")
    return {
        key: row
        for key, row in zip(keys, lookup.to_dict(orient="records"))
        if key
    }


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _weather_condition(code: float) -> str:
    if pd.isna(code):
        return ""
    code = int(code)
    if code == 0:
        return "Clear"
    if code in (1, 2, 3):
        return "Cloudy"
    if code in (45, 48):
        return "Fog"
    if code in (51, 53, 55, 56, 57):
        return "Drizzle"
    if code in (61, 63, 65, 66, 67):
        return "Rain"
    if code in (71, 73, 75, 77):
        return "Snow"
    if code in (80, 81, 82, 85, 86):
        return "Showers"
    if code in (95, 96, 99):
        return "Thunderstorm"
    return "Unknown"


def _build_tables(raw_results: pd.DataFrame, raw_weather: pd.DataFrame) -> dict[str, pd.DataFrame]:
    required_results = {
        "season",
        "round",
        "race_name",
        "date",
        "circuit_name",
        "position",
        "points",
        "grid_position",
        "status",
        "driver_code",
        "driver_given_name",
        "driver_family_name",
        "constructor_name",
        "race_type",
    }
    missing = required_results - set(raw_results.columns)
    if missing:
        raise ValueError(f"Race results file is missing columns: {sorted(missing)}")

    required_weather = {
        "time_utc",
        "season",
        "round",
        "circuit_name",
        "latitude",
        "longitude",
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation",
        "wind_speed_10m",
        "weather_code",
    }
    missing = required_weather - set(raw_weather.columns)
    if missing:
        raise ValueError(f"Weather file is missing columns: {sorted(missing)}")

    results = raw_results.copy()
    results["season"] = _numeric(results["season"]).astype("Int64")
    results["round"] = _numeric(results["round"]).astype("Int64")
    results["date"] = pd.to_datetime(results["date"], errors="coerce").dt.date
    results["driver_code"] = results["driver_code"].fillna("").str.strip().str.upper()
    results["driver_given_name"] = results["driver_given_name"].fillna("").str.strip()
    results["driver_family_name"] = results["driver_family_name"].fillna("").str.strip()
    results["circuit_name"] = results["circuit_name"].fillna("").str.strip()
    results["constructor_name"] = results["constructor_name"].fillna("").str.strip()
    results["race_type"] = results["race_type"].fillna("").str.strip().str.lower()
    results["driver_ref"] = results.apply(
        lambda row: _slug(row["driver_code"])
        or _slug(f"{row['driver_given_name']} {row['driver_family_name']}"),
        axis=1,
    )
    valid_keys = (
        results["season"].notna()
        & results["round"].notna()
        & results["date"].notna()
        & results["driver_ref"].ne("")
        & results["circuit_name"].ne("")
    )
    invalid_count = int((~valid_keys).sum())
    results = results.loc[valid_keys].copy()

    sprint_count = int(results["race_type"].eq("sprint").sum())
    unrecognized_count = int((~results["race_type"].isin(["main_race", "sprint"])).sum())
    results = results.loc[results["race_type"].isin(["main_race", "sprint"])].copy()
    results["points"] = _numeric(results["points"])
    invalid_points_count = int(results["points"].isna().sum())
    results = results.loc[results["points"].notna()].copy()
    race_results = results.loc[results["race_type"].eq("main_race")].copy()
    invalid_main_count = int(
        (_numeric(race_results["grid_position"]).isna()
         | _numeric(race_results["position"]).isna()).sum()
    )
    race_results = race_results.loc[
        _numeric(race_results["grid_position"]).notna()
        & _numeric(race_results["position"]).notna()
    ].copy()
    duplicate_mask = race_results.duplicated(["season", "round", "driver_ref"], keep="first")
    duplicate_count = int(duplicate_mask.sum())
    race_results = race_results.loc[~duplicate_mask].copy()
    if race_results.empty:
        raise ValueError("No valid main-race result rows remain after filtering.")

    # Race IDs use the season/round natural key, shared by results and weather.
    race_keys = sorted(
        race_results[["season", "round"]].drop_duplicates().itertuples(index=False, name=None)
    )
    race_ids = {key: index for index, key in enumerate(race_keys, start=1)}
    race_results["race_id"] = [
        race_ids[(int(season), int(round_number))]
        for season, round_number in zip(race_results["season"], race_results["round"])
    ]

    circuit_names = sorted(race_results["circuit_name"].unique())
    circuit_ids = {name: index for index, name in enumerate(circuit_names, start=1)}
    circuit_lookup = _read_manual_lookup("circuits.csv", "circuit_name")
    weather = raw_weather.copy()
    weather["season"] = _numeric(weather["season"]).astype("Int64")
    weather["round"] = _numeric(weather["round"]).astype("Int64")
    weather["time_utc"] = pd.to_datetime(weather["time_utc"], utc=True, errors="coerce")
    for column in (
        "latitude",
        "longitude",
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation",
        "wind_speed_10m",
        "weather_code",
    ):
        weather[column] = _numeric(weather[column])
    weather["circuit_name"] = weather["circuit_name"].fillna("").str.strip()

    coordinate_lookup = (
        weather.dropna(subset=["latitude", "longitude"])
        .groupby("circuit_name")[["latitude", "longitude"]]
        .first()
        .to_dict(orient="index")
    )
    circuit_rows = []
    for name in circuit_names:
        manual = circuit_lookup.get(_slug(name), {})
        coordinates = coordinate_lookup.get(name, {})
        circuit_rows.append(
            {
                "circuit_id": circuit_ids[name],
                "circuit_ref": manual.get("circuit_ref") or _slug(name),
                "circuit_name": name,
                "locality": manual.get("locality", ""),
                "country": manual.get("country", ""),
                "latitude": manual.get("latitude") or coordinates.get("latitude", pd.NA),
                "longitude": manual.get("longitude") or coordinates.get("longitude", pd.NA),
            }
        )
    dim_circuit = pd.DataFrame(circuit_rows, columns=TABLE_COLUMNS["dim_circuit"])

    driver_codes = _read_manual_lookup("drivers.csv", "driver_code")
    driver_records = (
        results.sort_values(["season", "round"])
        .drop_duplicates("driver_ref")
        .copy()
    )
    driver_ids = {
        driver_ref: index
        for index, driver_ref in enumerate(sorted(driver_records["driver_ref"]), start=1)
    }
    driver_rows = []
    for row in driver_records.to_dict(orient="records"):
        manual = driver_codes.get(_slug(row["driver_code"]), {})
        driver_rows.append(
            {
                "driver_id": driver_ids[row["driver_ref"]],
                "driver_ref": row["driver_ref"],
                "driver_code": row["driver_code"] or manual.get("driver_code", ""),
                "full_name": " ".join(
                    part
                    for part in (
                        row["driver_given_name"],
                        row["driver_family_name"],
                    )
                    if part
                )
                or manual.get("full_name", ""),
                "date_of_birth": manual.get("date_of_birth", ""),
                "nationality": manual.get("nationality", ""),
            }
        )
    dim_driver = pd.DataFrame(driver_rows, columns=TABLE_COLUMNS["dim_driver"])
    race_results["driver_id"] = race_results["driver_ref"].map(driver_ids)

    dim_race = (
        race_results[
            ["race_id", "season", "round", "race_name", "date", "circuit_name"]
        ]
        .drop_duplicates(["season", "round"])
        .copy()
    )
    dim_race["season_year"] = dim_race.pop("season")
    dim_race["circuit_id"] = dim_race["circuit_name"].map(circuit_ids)
    dim_race["race_date"] = dim_race.pop("date").astype(str)
    dim_race = dim_race[TABLE_COLUMNS["dim_race"]]

    team_names = sorted(name for name in results["constructor_name"].unique() if name)
    team_ids = {name: index for index, name in enumerate(team_names, start=1)}
    race_results["team_id"] = race_results["constructor_name"].map(team_ids).astype("Int64")
    race_results["grid_position"] = _numeric(race_results["grid_position"]).astype("Int64")
    race_results["finishing_position"] = _numeric(race_results["position"]).astype("Int64")
    race_results["points"] = _numeric(race_results["points"])
    classified_status = race_results["status"].fillna("").str.strip().str.fullmatch(
        r"(?:finished|lapped|\+?\d+\s+laps?)", case=False
    )
    race_results["is_dnf"] = ~classified_status
    race_results = race_results.sort_values(["season", "round", "driver_id"])
    fact_race_result = pd.DataFrame(
        {
            "race_id": race_results["race_id"],
            "driver_id": race_results["driver_id"],
            "team_id": race_results["team_id"],
            "grid_position": race_results["grid_position"],
            "finishing_position": race_results["finishing_position"],
            "points": race_results["points"],
            "fastest_lap_time": pd.NA,
            "result_id": range(1, len(race_results) + 1),
            "is_dnf": race_results["is_dnf"],
        },
        columns=TABLE_COLUMNS["fact_race_result"],
    )

    # Points include sprint and main-race points; the saved outcome table remains
    # main-race-only. Counts are computed over the complete input before emitting standings.
    all_results = results.copy()
    all_results["points_value"] = all_results["points"]
    all_results["position_value"] = _numeric(all_results["position"])
    standing_rows = []
    standing_id = 1
    for season, season_results in all_results.groupby("season", sort=True):
        totals: dict[int, dict[str, Any]] = {}
        for round_number, weekend in season_results.groupby("round", sort=True):
            for _, result in weekend.iterrows():
                driver_id = int(driver_ids[result["driver_ref"]])
                driver_totals = totals.setdefault(
                    driver_id,
                    {
                        "points_after": 0.0,
                        "wins_after": 0,
                        "team_id": pd.NA,
                    },
                )
                driver_totals["points_after"] += float(result["points_value"])
                driver_totals["wins_after"] += int(
                    result["race_type"] == "main_race"
                    and result["position_value"] == 1
                )
                if result["constructor_name"]:
                    driver_totals["team_id"] = team_ids[result["constructor_name"]]

            race_id = race_ids.get((int(season), int(round_number)))
            if race_id is None:
                continue

            ranked = sorted(
                totals.items(),
                key=lambda item: (
                    -item[1]["points_after"],
                    -item[1]["wins_after"],
                    item[0],
                ),
            )
            for position, (driver_id, driver_totals) in enumerate(ranked, start=1):
                standing_rows.append(
                    {
                        "standing_id": standing_id,
                        "race_id": race_id,
                        "driver_id": driver_id,
                        "team_id": driver_totals["team_id"],
                        "position_after": position,
                        "points_after": driver_totals["points_after"],
                        "wins_after": driver_totals["wins_after"],
                    }
                )
                standing_id += 1
    fact_driver_standing = pd.DataFrame(
        standing_rows,
        columns=TABLE_COLUMNS["fact_driver_standing"],
    )

    weather = weather.dropna(subset=["time_utc", "season", "round"])
    invalid_weather_count = len(raw_weather) - len(weather)
    weather["race_id"] = [
        race_ids.get((int(season), int(round_number)), pd.NA)
        for season, round_number in zip(weather["season"], weather["round"])
    ]
    unmatched_weather_count = int(weather["race_id"].isna().sum())
    weather = weather.dropna(subset=["race_id"])
    weather["race_id"] = weather["race_id"].astype(int)
    weather_summary = (
        weather.groupby("race_id")
        .agg(
            temperature=("temperature_2m", "mean"),
            humidity=("relative_humidity_2m", "mean"),
            wind_speed=("wind_speed_10m", "mean"),
            precipitation=("precipitation", "sum"),
            weather_code=("weather_code", lambda values: values.mode().iloc[0]
                          if not values.mode().empty else pd.NA),
        )
        .reset_index()
        .sort_values("race_id")
    )
    fact_weather = pd.DataFrame(
        {
            "weather_id": range(1, len(weather_summary) + 1),
            "race_id": weather_summary["race_id"],
            "temperature": weather_summary["temperature"],
            "humidity": weather_summary["humidity"],
            "wind_speed": weather_summary["wind_speed"],
            "precipitation": weather_summary["precipitation"],
            "weather_condition": weather_summary["weather_code"].map(_weather_condition),
        },
        columns=TABLE_COLUMNS["fact_weather"],
    )

    race_results = race_results.sort_values(["season", "round", "driver_id"]).copy()
    points_by_driver = race_results.groupby("driver_id", sort=False)["points"]
    race_results["driver_points_before_race"] = points_by_driver.transform(
        lambda points: points.cumsum().shift(1).fillna(0)
    )
    race_results["driver_avg_points_last_3_before_race"] = points_by_driver.transform(
        lambda points: points.shift(1).rolling(window=3, min_periods=1).mean().fillna(0)
    )
    race_results["driver_starts_before_race"] = race_results.groupby(
        "driver_id", sort=False
    ).cumcount()

    sprint_races = {
        (int(season), int(round_number))
        for season, round_number in results.loc[
            results["race_type"].eq("sprint"), ["season", "round"]
        ].drop_duplicates().itertuples(index=False, name=None)
    }
    race_results["sprint_weekend"] = [
        (int(season), int(round_number)) in sprint_races
        for season, round_number in zip(race_results["season"], race_results["round"])
    ]
    race_results["season_year"] = race_results["season"].astype(int)
    race_results["round"] = race_results["round"].astype(int)
    race_results["split"] = race_results["season_year"].map(
        {
            2021: "train",
            2022: "train",
            2023: "train",
            2024: "validate",
            2025: "test",
        }
    )
    race_month = pd.to_datetime(race_results["date"]).dt.month
    for month in range(1, 13):
        race_results[f"race_month_{month:02d}"] = race_month.eq(month)

    feature_data = {
        "feature_id": range(1, len(race_results) + 1),
        "race_id": race_results["race_id"],
        "driver_id": race_results["driver_id"],
        "season_year": race_results["season_year"],
        "round": race_results["round"],
        "target_points": race_results["points"],
        "grid_position": race_results["grid_position"],
        "driver_points_before_race": race_results["driver_points_before_race"],
        "driver_avg_points_last_3_before_race": race_results[
            "driver_avg_points_last_3_before_race"
        ],
        "driver_starts_before_race": race_results["driver_starts_before_race"],
        "sprint_weekend": race_results["sprint_weekend"],
        "split": race_results["split"],
    }
    feature_data.update(
        {
            f"race_month_{month:02d}": race_results[f"race_month_{month:02d}"]
            for month in range(1, 13)
        }
    )
    ml_features = pd.DataFrame(
        feature_data,
        columns=TABLE_COLUMNS["ml_features_race_outcome"],
    )
    if ml_features["split"].isna().any():
        unknown_seasons = sorted(
            race_results.loc[race_results["split"].isna(), "season_year"].unique()
        )
        raise ValueError(
            "ML feature split is undefined for seasons: "
            f"{unknown_seasons}. Expected seasons 2021 through 2025."
        )

    tables = {
        "dim_circuit": dim_circuit,
        "dim_driver": dim_driver,
        "dim_race": dim_race,
        "fact_race_result": fact_race_result,
        "fact_driver_standing": fact_driver_standing,
        "fact_weather": fact_weather,
        "ml_features_race_outcome": ml_features,
    }
    for name, dataframe in tables.items():
        tables[name] = dataframe.reindex(columns=TABLE_COLUMNS[name])

    print(f"Filtered out {sprint_count} sprint rows: only main races are the prediction unit.")
    print(f"Filtered out {unrecognized_count} rows with unrecognized race_type.")
    print(f"Filtered out {invalid_count} rows with missing/invalid natural keys.")
    print(f"Filtered out {invalid_points_count} rows with missing/invalid points.")
    print(f"Filtered out {invalid_main_count} main-race rows with invalid grid/finish positions.")
    print(f"Filtered out {duplicate_count} duplicate driver/main-race rows.")
    print(
        f"Excluded {invalid_weather_count} invalid hourly weather rows and "
        f"{unmatched_weather_count} rows without a matching main-race key."
    )
    if results["constructor_name"].eq("").any():
        warnings.warn(
            "Constructor names are missing in the raw results; team_id is blank in "
            "fact tables. The raw extractor must populate each result's Constructor.",
            stacklevel=2,
        )
    for table, column in (
        ("dim_circuit", "country"),
        ("dim_driver", "date_of_birth"),
        ("dim_driver", "nationality"),
    ):
        missing_values = int(tables[table][column].fillna("").astype(str).str.strip().eq("").sum())
        if missing_values:
            warnings.warn(
                f"{table}.{column} is missing for {missing_values} rows. "
                f"Add {MANUAL_DIR / ('circuits.csv' if table == 'dim_circuit' else 'drivers.csv')} "
                "with the corresponding lookup data.",
                stacklevel=2,
            )
    return tables


def transform() -> dict[str, pd.DataFrame]:
    """Read raw extracts and return one DataFrame for every active schema table."""
    race_path = _one_file(RAW_DIR, RAW_RACE_PATTERN)
    weather_path = _one_file(RAW_DIR, RAW_WEATHER_PATTERN)
    raw_results = pd.read_csv(race_path, dtype=str).fillna("")
    raw_weather = pd.read_csv(weather_path)
    return _build_tables(raw_results, raw_weather)


def main() -> None:
    tables = transform()
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    for table_name, dataframe in tables.items():
        output_path = CLEAN_DIR / f"{table_name}.csv"
        dataframe.to_csv(output_path, index=False)
        print(f"Wrote {len(dataframe)} rows to {output_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()