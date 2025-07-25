import requests
from datetime import datetime, timedelta

API_KEY = ""
BASE_URL = "http://api.aviationstack.com/v1/flights"

def fetch_arrivals_by_airport(airport_iata: str, date_from: str = None, date_to: str = None):
    params = {
        "access_key": API_KEY,
        "arr_icao": airport_iata,
    }
    if date_from:
        params["flight_date"] = date_from
    if date_to:
        params["flight_date_to"] = date_to

    resp = requests.get(BASE_URL, params=params)
    resp.raise_for_status()
    data = resp.json()

    if "data" not in data:
        raise Exception(f"Unexpected response format: {data}")

    return data["data"]

def get_luton_flights(flight_date: str = None):
    return fetch_arrivals_by_airport("EGGW", date_from=flight_date)

if __name__ == "__main__":
    # date format: YYYY-MM-DD
    today = datetime.utcnow().strftime("%Y-%m-%d")
    arrivals = get_luton_flights(today)
    print(f"Found {len(arrivals)} arrivals on {today}:")
    for f in arrivals:
        print(f"{f.get('flight_date')} | {f.get('flight_status')} | from {f.get('departure', {}).get('airport')}")