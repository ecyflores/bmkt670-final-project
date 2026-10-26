from datetime import timedelta
import time
from pathlib import Path

import openmeteo_requests
import pandas as pd
import requests
import requests_cache
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

JOLPICA_API_URL = "https://api.jolpi.ca/ergast/f1"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
START_SEASON = 2021
END_SEASON = 2025
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT_FILE = RAW_DIR / f"f1_weather_{START_SEASON}_{END_SEASON}.csv"
REQUEST_DELAY_SECONDS = 1.0
RAW_DIR.mkdir(parents=True, exist_ok=True)
HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "wind_speed_10m",
    "weather_code",
]

retry_policy = Retry(
    total=6,
    connect=6,
    read=6,
    status=6,
    backoff_factor=2,
    backoff_max=120,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=frozenset({"GET"}),
    respect_retry_after_header=True,
)
cache_session = requests_cache.CachedSession(
    str(RAW_DIR / ".openmeteo_cache"),
    expire_after=30 * 24 * 60 * 60,
)
cache_session.mount("https://", HTTPAdapter(max_retries=retry_policy))
cache_session.headers.update({"User-Agent": "bmkt670-f1-data-project/1.0"})
openmeteo = openmeteo_requests.Client(session=cache_session)


def get_season_calendar(season: int) -> list[dict]:
    """Fetch race dates and circuit coordinates for a season."""
    url = f"{JOLPICA_API_URL}/{season}.json"
    try:
        response = cache_session.get(url, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as error:
        raise RuntimeError(f"Jolpica calendar request failed for {url}: {error}") from error
    return response.json()["MRData"]["RaceTable"]["Races"]


def get_race_weekend_weather(season: int, race: dict) -> pd.DataFrame:
    """Fetch hourly historical weather at a circuit from Friday through race day."""
    circuit = race["Circuit"]
    race_date = pd.to_datetime(race["date"]).date()
    weekend_start = race_date - timedelta(days=2)
    params = {
        "latitude": float(circuit["Location"]["lat"]),
        "longitude": float(circuit["Location"]["long"]),
        "start_date": weekend_start.isoformat(),
        "end_date": race_date.isoformat(),
        "hourly": HOURLY_VARIABLES,
        "timezone": "auto",
    }

    try:
        response = openmeteo.weather_api(OPEN_METEO_ARCHIVE_URL, params=params)[0]
    except requests.exceptions.RequestException as error:
        raise RuntimeError(
            f"Open-Meteo request failed for {race['raceName']} ({season}): {error}"
        ) from error
    hourly = response.Hourly()
    times = pd.date_range(
        start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
        end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=hourly.Interval()),
        inclusive="left",
    )
    weather_data = {
        "time_utc": times,
        "season": season,
        "round": int(race["round"]),
        "race_name": race["raceName"],
        "circuit_name": circuit["circuitName"],
        "latitude": params["latitude"],
        "longitude": params["longitude"],
    }
    for index, variable in enumerate(HOURLY_VARIABLES):
        weather_data[variable] = hourly.Variables(index).ValuesAsNumpy()

    return pd.DataFrame(weather_data)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    weather_frames = []

    for season in range(START_SEASON, END_SEASON + 1):
        print(f"Fetching race weekends for {season}")
        for race in get_season_calendar(season):
            print(f"  {race['raceName']} ({race['date']})")
            weather_frames.append(get_race_weekend_weather(season, race))
            time.sleep(REQUEST_DELAY_SECONDS)

    if not weather_frames:
        raise RuntimeError("No race weekend weather data was retrieved.")

    weather = pd.concat(weather_frames, ignore_index=True)
    weather.to_csv(OUTPUT_FILE, index=False)
    print(f"Wrote {len(weather)} hourly observations to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
