import requests
from datetime import datetime, timedelta
from app import models
from sqlalchemy.orm import Session
from fastapi import HTTPException
from sqlalchemy import func
from datetime import datetime

API_KEY = ""
BASE_URL = "http://api.aviationstack.com/v1/flights"

def parse_iso(timestamp):
    if timestamp:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return None

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

def fetch_departures_by_airport(airport_iata: str, date_from: str = None, date_to: str = None):
    params = {
        "access_key": API_KEY,
        "dep_icao": airport_iata,
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
    return {
        "arrivals": fetch_arrivals_by_airport("EGGW", date_from=flight_date),
        "departures": fetch_departures_by_airport("EGGW", date_from=flight_date)
    }

def store_luton_flights(db: Session, flight_date: str = None):
    flights = get_luton_flights(flight_date=flight_date)

    for flight in flights["arrivals"]:
        actual_departure = parse_iso(flight.get("departure", {}).get("actual"))
        actual_arrival = parse_iso(flight.get("arrival", {}).get("actual"))

        if actual_departure and actual_arrival:
            duration = calculate_flight_duration(actual_departure.isoformat(), actual_arrival.isoformat())
        else:
            duration = None
        db.add(models.Flight(
            flight_number=flight["flight"]["iataNumber"] or flight["flight"]["icaoNumber"],
            origin=flight.get("departure", {}).get("iataCode"),
            destination="EGGW",
            direction="arrival",
            duration_minutes=duration
        ))

    for flight in flights["departures"]:
        actual_departure = parse_iso(flight.get("departure", {}).get("actual"))
        actual_arrival = parse_iso(flight.get("arrival", {}).get("actual"))

        if actual_departure and actual_arrival:
            duration = calculate_flight_duration(actual_departure.isoformat(), actual_arrival.isoformat())
        else:
            duration = None
        db.add(models.Flight(
            flight_number=flight["flight"]["iataNumber"] or flight["flight"]["icaoNumber"],
            origin="EGGW",
            destination=flight.get("arrival", {}).get("iataCode"),
            direction="departure",
            duration_minutes=duration
        ))

    db.commit()

def validate_flight_assignment(
    db: Session,
    crew_id: int,
    flight: models.Flight,
    departure_time,
    arrival_time
):
    #geting all flights for this crew on the same date
    schedules_today = db.query(models.CrewSchedule).filter(
        models.CrewSchedule.crew_id == crew_id,
        func.date(models.CrewSchedule.departure_time) == departure_time.date()
    ).all()

    #checking for duplicate direction assignment
    for schedule in schedules_today:
        if schedule.flight_number == flight.flight_number:
            raise HTTPException(status_code=400, detail="Crew already assigned to this flight.")

        #only 1 departure and 1 arrival allowed
        if flight.direction == "departure" and schedule.departure_time == departure_time:
            raise HTTPException(status_code=400, detail="Crew already has a departure at this time.")
        if flight.direction == "arrival" and schedule.arrival_time == arrival_time:
            raise HTTPException(status_code=400, detail="Crew already has an arrival at this time.")

    if flight.direction == "arrival":
        #checking if at least one departure was assigned before
        departures_today = [
            s for s in schedules_today
            if db.query(models.Flight).filter(models.Flight.id == s.flight_id, models.Flight.direction == "departure").first()
        ]
        if not departures_today:
            raise HTTPException(status_code=400, detail="Arrival flight cannot be assigned before a departure on the same day.")

        latest_departure = max(departures_today, key=lambda x: x.departure_time)
        min_arrival_time = latest_departure.departure_time + timedelta(hours=1)
        if arrival_time < min_arrival_time:
            raise HTTPException(status_code=400, detail="Arrival is unrealistically soon after departure.")
        
def calculate_flight_duration(departure_iso: str, arrival_iso: str) -> int | None:
    from datetime import datetime

    def parse_iso(timestamp):
        if timestamp:
            return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return None

    dep = parse_iso(departure_iso)
    arr = parse_iso(arrival_iso)

    if dep and arr:
        return int((arr - dep).total_seconds() / 60)
    return None
