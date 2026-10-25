from datetime import timedelta
import time
import openmeteo_requests
import pandas as pd
import requests
import requests_cache
from retry_requests import retry

JOLPICA_API_URL = "https://api.jolpi.ca/ergast/f1"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
START_SEASON = 2021
END_SEASON = 2025
OUTPUT_FILE = f"f1_weather_{START_SEASON}_{END_SEASON}.csv"
HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "wind_speed_10m",
    "weather_code",
]

cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)


def get_season_calendar(season: int) -> list[dict]:
    """Fetch race dates and circuit coordinates for a season."""
    response = requests.get(f"{JOLPICA_API_URL}/{season}.json", timeout=30)
    response.raise_for_status()
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

    response = openmeteo.weather_api(OPEN_METEO_ARCHIVE_URL, params=params)[0]
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
    weather_frames = []

    for season in range(START_SEASON, END_SEASON + 1):
        print(f"Fetching race weekends for {season}")
        for race in get_season_calendar(season):
            print(f"  {race['raceName']} ({race['date']})")
            weather_frames.append(get_race_weekend_weather(season, race))
            time.sleep(0.5)

    if not weather_frames:
        raise RuntimeError("No race weekend weather data was retrieved.")

    weather = pd.concat(weather_frames, ignore_index=True)
    weather.to_csv(OUTPUT_FILE, index=False)
    print(f"Wrote {len(weather)} hourly observations to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
