import fastf1
from fastf1 import plotting
import pandas as pd

import requests
import csv
import sys
import time

API_BASE_URL = "https://api.jolpi.ca/ergast/f1"

def get_season_calendar(season: int):
    """Fetches the race calendar for a given F1 season."""
    url = f"{API_BASE_URL}/{season}.json"
    print(f"Fetching season calendar from: {url}")

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data['MRData']['RaceTable']['Races']
    except requests.exceptions.RequestException as e:
        print(f"Error fetching calendar: {e}")
        return None
    except KeyError:
        print("Error: Could not find 'Races' data in calendar response.")
        return None

def get_race_results(season: int, race_round: int):
    """Fetches the results for a single race (including sprint if available) by its season and round number."""
    all_results_for_round = []

    # Fetch main race results
    main_race_url = f"{API_BASE_URL}/{season}/{race_round}/results.json?limit=100"
    print(f"Fetching main race results for round {race_round}...{main_race_url}")
    try:
        response = requests.get(main_race_url, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data['MRData']['RaceTable']['Races']:
            main_race_data = data['MRData']['RaceTable']['Races'][0]
            # Add a 'type' key to distinguish between main race and sprint
            main_race_data['type'] = 'main_race'
            all_results_for_round.append(main_race_data)
        else:
            print(f"  -> No main race results found for round {race_round} (likely not raced yet).")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching main race results for round {race_round}: {e}")
    except KeyError:
        print(f"Error: Could not parse main race results data for round {race_round}.")

    # Fetch sprint race results (if available)
    sprint_url = f"{API_BASE_URL}/{season}/{race_round}/sprint.json?limit=100"
    print(f"Fetching sprint race results for round {race_round}...{sprint_url}")
    try:
        response = requests.get(sprint_url, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data['MRData']['RaceTable']['Races']:
            sprint_data = data['MRData']['RaceTable']['Races'][0]
            # Add a 'type' key to distinguish between main race and sprint
            sprint_data['type'] = 'sprint'
            all_results_for_round.append(sprint_data)
        else:
             print(f"  -> No sprint race results found for round {race_round}.")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching sprint race results for round {race_round}: {e}")
    except KeyError:
        print(f"Error: Could not parse sprint race results data for round {race_round}.")


    return all_results_for_round if all_results_for_round else None


def write_results_to_csv(all_races_and_sprints: list, filename: str):
    """Writes a consolidated list of race and sprint results into a single CSV file."""
    if not all_races_and_sprints:
        print("No race or sprint results to write. Exiting.")
        return

    headers = [
        'season', 'round', 'race_name', 'date', 'circuit_name',
        'position', 'points', 'grid_position', 'laps', 'status',
        'driver_number', 'driver_code', 'driver_given_name', 'driver_family_name',
        'constructor_name', 'constructor_nationality', 'race_type' # Added 'race_type' header
    ]

    written_rows = 0
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()

            for race_event_results in all_races_and_sprints:
                # A race event might be in the calendar but have no results yet (either main or sprint)
                if 'Results' not in race_event_results:
                    continue

                # Add a diagnostic print here
                event_type = race_event_results.get('type', 'unknown')
                print(f"Processing {event_type} for round {race_event_results.get('round')}")


                for result in race_event_results['Results']:
                    writer.writerow({
                        'season': race_event_results.get('season'),
                        'round': race_event_results.get('round'),
                        'race_name': race_event_results.get('raceName'),
                        'date': race_event_results.get('date'),
                        'circuit_name': race_event_results.get('Circuit', {}).get('circuitName'),
                        'position': result.get('position'),
                        'points': result.get('points'),
                        'grid_position': result.get('grid'),
                        'laps': result.get('laps'),
                        'status': result.get('status'),
                        'driver_number': result.get('Driver', {}).get('permanentNumber'),
                        'driver_code': result.get('Driver', {}).get('code'),
                        'driver_given_name': result.get('Driver', {}).get('givenName'),
                        'driver_family_name': result.get('Driver', {}).get('familyName'),
                        'constructor_name': race_event_results.get('Constructor', {}).get('name'),
                        'constructor_nationality': race_event_results.get('Constructor', {}).get('nationality'),
                        'race_type': event_type # Use the determined event type
                    })
                    written_rows += 1

        print(f"\nSuccessfully wrote {written_rows} results from {len(all_races_and_sprints)} events to {filename}")

    except IOError as e:
        print(f"Error writing to file {filename}: {e}")



def write_results_to_csv02(all_races_and_sprints: list, filename: str):
    """Writes a consolidated list of race and sprint results into a single CSV file."""
    if not all_races_and_sprints:
        print("No race or sprint results to write. Exiting.")
        return

    headers = [
        'season', 'round', 'race_name', 'date', 'circuit_name',
        'position', 'points', 'grid_position', 'laps', 'status',
        'driver_number', 'driver_code', 'driver_given_name', 'driver_family_name',
        'constructor_name', 'constructor_nationality', 'race_type' # Added 'race_type' header
    ]

    written_rows = 0
    try:
        with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            #writer.writeheader()

            for race_event_results in all_races_and_sprints:
                # A race event might be in the calendar but have no results yet (either main or sprint)
                if 'SprintResults' not in race_event_results:
                    continue

                # Add a diagnostic print here
                event_type = race_event_results.get('type', 'unknown')
                print(f"Processing {event_type} for round {race_event_results.get('round')}")


                for result in race_event_results['SprintResults']:
                    writer.writerow({
                        'season': race_event_results.get('season'),
                        'round': race_event_results.get('round'),
                        'race_name': race_event_results.get('raceName'),
                        'date': race_event_results.get('date'),
                        'circuit_name': race_event_results.get('Circuit', {}).get('circuitName'),
                        'position': result.get('position'),
                        'points': result.get('points'),
                        'grid_position': result.get('grid'),
                        'laps': result.get('laps'),
                        'status': result.get('status'),
                        'driver_number': result.get('Driver', {}).get('permanentNumber'),
                        'driver_code': result.get('Driver', {}).get('code'),
                        'driver_given_name': result.get('Driver', {}).get('givenName'),
                        'driver_family_name': result.get('Driver', {}).get('familyName'),
                        'constructor_name': race_event_results.get('Constructor', {}).get('name'),
                        'constructor_nationality': race_event_results.get('Constructor', {}).get('nationality'),
                        'race_type': event_type # Use the determined event type
                    })
                    written_rows += 1

        print(f"\nSuccessfully wrote {written_rows} results from {len(all_races_and_sprints)} events to {filename}")

    except IOError as e:
        print(f"Error writing to file {filename}: {e}")



if __name__ == "__main__":
    SEASON_YEAR = 2025
    OUTPUT_FILE = f"f1_{SEASON_YEAR}_all_race_sprint_results.csv"

    print(f"<<<Season Year: {SEASON_YEAR}")

    # 1. Get the calendar for the season
    season_calendar = get_season_calendar(SEASON_YEAR)
    print("<<<Get the calendar for the season: {SEASON_YEAR}")

    if season_calendar:
        all_results_data = []

        # 2. Iterate through each race in the calendar
        for race_event in season_calendar:
            race_round = int(race_event['round'])

            # 3. Fetch the results for that specific round (includes main and sprint if available)
            race_and_sprint_results = get_race_results(SEASON_YEAR, race_round)

            # Add diagnostic print here
            print(f"Returned results for round {race_round}: {race_and_sprint_results}")


            # 4. If results were successfully returned (either main or sprint or both), add them to our list
            if race_and_sprint_results:
                all_results_data.extend(race_and_sprint_results)

            # Be a good API citizen by waiting a moment between requests
            time.sleep(0.5)

        # 5. Write all the collected results to a single CSV file
        write_results_to_csv(all_results_data, OUTPUT_FILE) #Race Results
        write_results_to_csv02(all_results_data, OUTPUT_FILE) #Adding Sprint Results
    else:
        sys.exit(1)



# source: https://python.plainenglish.io/get-all-the-f1-season-results-in-5-minutes-with-python-jolpica-api-6ec13e6efac5