import requests
from datetime import datetime, timedelta, timezone
import pytz
from zoneinfo import ZoneInfo
from app import models
from sqlalchemy.orm import Session
from fastapi import HTTPException
from sqlalchemy import func

API_KEY = ""
BASE_URL = "http://api.aviationstack.com/v1/flights"

def get_gmt_offset_from_timezone(timezone_name: str, reference_date: datetime = None) -> str:
    """
    TBC:
    convert timezone name like 'Europe/Paris' to GMT offset like 'GMT+2'.
    """
    if not timezone_name:
        return "GMT+0"
    
    try:
        if reference_date is None:
            reference_date = datetime.now()
        
        tz = ZoneInfo(timezone_name)
        dt_with_tz = reference_date.replace(tzinfo=tz)
        
        #get  UTC offset
        offset = dt_with_tz.utcoffset()
        if offset is None:
            return "GMT+0"
        
        # hours and minutes offset
        total_seconds = int(offset.total_seconds())
        hours = total_seconds // 3600
        minutes = abs(total_seconds % 3600) // 60
        
        #format as GMT+X or GMT-X
        if hours >= 0:
            if minutes == 0:
                return f"GMT+{hours}"
            else:
                return f"GMT+{hours}:{minutes:02d}"
        else:
            if minutes == 0:
                return f"GMT{hours}"
            else:
                return f"GMT{hours}:{minutes:02d}"
                
    except Exception as e:
        print(f"Error converting timezone {timezone_name}: {e}")
        return "GMT+0"

def parse_aviationstack_timestamp(timestamp: str, timezone_name: str = None):
    if not timestamp:
        return None, None, None

    try:
        # parsing the UTC timestamp from API
        #handling both "Z" and "+00:00" formats
        if timestamp.endswith("Z"):
            dt_utc = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        else:
            dt_utc = datetime.fromisoformat(timestamp)
        
        if dt_utc.tzinfo is None:
            dt_utc = dt_utc.replace(tzinfo=timezone.utc)
        
        if timezone_name:
            try:
                local_tz = ZoneInfo(timezone_name)
                dt_local = dt_utc.astimezone(local_tz)
                gmt_offset = get_gmt_offset_from_timezone(timezone_name, dt_local)
                
                print(f"[TIMEZONE] {timestamp} UTC → {dt_local.strftime('%Y-%m-%d %H:%M')} {gmt_offset} ({timezone_name})")
                return dt_local, timezone_name, gmt_offset
            except Exception as e:
                print(f"[TIMEZONE] Failed to convert to {timezone_name}: {e}")
                return dt_utc, "UTC", "GMT+0"
        
        return dt_utc, "UTC", "GMT+0"
        
    except Exception as e:
        print(f"[TIMEZONE] Failed to parse {timestamp}: {e}")
        return None, None, None

def calculate_realistic_flight_duration(dep_local: datetime, arr_local: datetime, 
                                       dep_gmt_offset: str, arr_gmt_offset: str):
    """
    TBC
    calculating flight duration according to timezone differences
    """
    if not dep_local or not arr_local:
        return 0, "0h 0m"

    try:
        print(f"[DURATION] Calculating flight duration:")
        print(f" Departure: {dep_local.strftime('%Y-%m-%d %H:%M')} {dep_gmt_offset}")
        print(f" Arrival: {arr_local.strftime('%Y-%m-%d %H:%M')} {arr_gmt_offset}")
        
        # Convert both to UTC for accurate calculation
        dep_utc = dep_local.astimezone(timezone.utc)
        arr_utc = arr_local.astimezone(timezone.utc)
        
        print(f"Departure UTC: {dep_utc.strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"Arrival UTC: {arr_utc.strftime('%Y-%m-%d %H:%M UTC')}")
        
        # Calculate duration in UTC
        duration_sec = (arr_utc - dep_utc).total_seconds()
        duration_min = int(duration_sec // 60)
        
        print(f"Duration: {duration_min} minutes ({duration_min // 60}h {duration_min % 60}m)")
        
        if duration_min <= 0:
            print(f"Invalid duration: {duration_min} minutes")
            return 0, "0h 0m"
        
        duration_text = f"{duration_min // 60}h {duration_min % 60}m"
        return duration_min, duration_text
        
    except Exception as e:
        print(f"[DURATION] Error: {e}")
        return 0, "0h 0m"

def debug_flight_times(flight_data, direction):
    """
    api response structure:
    {
        "flight": {"iata": "BA123", "icao": "BAW123"},
        "departure": {
            "iata": "LHR",
            "scheduled": "2025-01-15T14:30:00+00:00",
            "timezone": "Europe/London"
        },
        "arrival": {
            "iata": "JFK", 
            "scheduled": "2025-01-15T17:45:00+00:00",
            "timezone": "America/New_York"
        }
    }
    """
    flight_info = flight_data.get("flight", {})
    flight_number = flight_info.get("iata", "UNKNOWN")
    
    departure_data = flight_data.get("departure", {})
    arrival_data = flight_data.get("arrival", {})
    
    print(f"DEBUG: {direction.upper()} Flight {flight_number}")
    print(f"Raw API Data:")
    print(f"Departure: {departure_data.get('iata')} - {departure_data.get('scheduled')} (TZ: {departure_data.get('timezone')})")
    print(f"Arrival: {arrival_data.get('iata')} - {arrival_data.get('scheduled')} (TZ: {arrival_data.get('timezone')})")
    
    # test timezone conversion
    dep_time, dep_tz, dep_offset = parse_aviationstack_timestamp(
        departure_data.get("scheduled"), departure_data.get("timezone")
    )
    arr_time, arr_tz, arr_offset = parse_aviationstack_timestamp(
        arrival_data.get("scheduled"), arrival_data.get("timezone")
    )
    
    if dep_time and arr_time:
        duration_min, duration_text = calculate_realistic_flight_duration(
            dep_time, arr_time, dep_offset, arr_offset
        )
        print(f"Final result: {duration_text}")
    
    print("=" * 50)

def fetch_arrivals_by_airport(airport_iata: str, date_from: str = None, date_to: str = None):
    params = {
        "access_key": API_KEY,
        "arr_iata": airport_iata,
    }
    if date_from:
        params["flight_date"] = date_from
    if date_to:
        params["flight_date_to"] = date_to

    try:
        resp = requests.get(BASE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

        if "data" not in data:
            raise Exception(f"Unexpected response format: {data}")

        return data["data"]
    except requests.RequestException as e:
        raise Exception(f"API request failed: {e}")

def fetch_departures_by_airport(airport_iata: str, date_from: str = None, date_to: str = None):
    params = {
        "access_key": API_KEY,
        "dep_iata": airport_iata,
    }
    if date_from:
        params["flight_date"] = date_from
    if date_to:
        params["flight_date_to"] = date_to

    try:
        resp = requests.get(BASE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

        if "data" not in data:
            raise Exception(f"Unexpected response format: {data}")

        return data["data"]
    except requests.RequestException as e:
        raise Exception(f"API request failed: {e}")

def get_luton_flights(flight_date: str = None):
    return {
        "arrivals": fetch_arrivals_by_airport("LTN", date_from=flight_date),
        "departures": fetch_departures_by_airport("LTN", date_from=flight_date)
    }

def store_luton_flights(db: Session, flight_date: str = None):
    flights = get_luton_flights(flight_date=flight_date)

    def process_flight_record(flight, direction):
        departure_data = flight.get("departure", {})
        arrival_data = flight.get("arrival", {})
        flight_info = flight.get("flight", {})
        flight_number = flight_info.get("iata") or flight_info.get("icao")
        
        if not flight_number:
            print("Skipping flight - no flight number")
            return
        
        print(f"PROCESSING: {direction} flight {flight_number}")
        print(f"Route: {departure_data.get('iata')} → {arrival_data.get('iata')}")

        dep_timezone = departure_data.get("timezone")
        arr_timezone = arrival_data.get("timezone")
        
        print(f"Timezones: {dep_timezone} → {arr_timezone}")

        dep_actual, dep_tz, dep_gmt = parse_aviationstack_timestamp(
            departure_data.get("actual"), dep_timezone
        )
        dep_scheduled, _, _ = parse_aviationstack_timestamp(
            departure_data.get("scheduled"), dep_timezone
        )
        departure_time = dep_actual or dep_scheduled
        
        arr_actual, arr_tz, arr_gmt = parse_aviationstack_timestamp(
            arrival_data.get("actual"), arr_timezone
        )
        arr_scheduled, _, _ = parse_aviationstack_timestamp(
            arrival_data.get("scheduled"), arr_timezone
        )
        arrival_time = arr_actual or arr_scheduled

        if not departure_time or not arrival_time:
            print("Skipping - missing times")
            return

        dep_utc = departure_time.astimezone(timezone.utc)
        arr_utc = arrival_time.astimezone(timezone.utc)
        
        if arr_utc <= dep_utc:
            print(f"ERROR: Arrival UTC ({arr_utc}) ≤ Departure UTC ({dep_utc})")
            debug_flight_times(flight, direction)
            return
        duration_min, duration_text = calculate_realistic_flight_duration(
            departure_time, arrival_time, dep_gmt or "GMT+0", arr_gmt or "GMT+0"
        )

        if duration_min <= 0 or duration_min > 12 * 60:
            print(f"Invalid duration: {duration_min} minutes")
            debug_flight_times(flight, direction)
            return

        origin_iata = departure_data.get("iata")
        destination_iata = arrival_data.get("iata")

        existing = db.query(models.Flight).filter(
            models.Flight.flight_number == flight_number,
            models.Flight.direction == direction,
            func.date(models.Flight.departure_time) == departure_time.date()
        ).first()

        if not existing:
            print(f"Storing: {duration_text} ({origin_iata} {dep_gmt} → {destination_iata} {arr_gmt})")
            
            db_flight = models.Flight(
                flight_number=flight_number,
                origin=origin_iata,
                destination=destination_iata,
                direction=direction,
                duration_minutes=duration_min,
                duration_text=duration_text,
                departure_time=departure_time,
                arrival_time=arrival_time,
                origin_timezone=dep_tz,
                destination_timezone=arr_tz,
                origin_gmt_offset=dep_gmt,
                destination_gmt_offset=arr_gmt
            )
            db.add(db_flight)
        else:
            print("Already exists")

    print("Processing {len(flights['arrivals'])} arrivals...")
    for flight in flights["arrivals"]:
        process_flight_record(flight, "arrival")

    print("Processing {len(flights['departures'])} departures...")
    for flight in flights["departures"]:
        process_flight_record(flight, "departure")

    db.commit()
    print("All flights committed to database")

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
        if (flight.direction == "departure" and 
            schedule.departure_time and 
            abs((schedule.departure_time - departure_time).total_seconds()) < 300):
            raise HTTPException(status_code=400, detail="Crew already has a departure around this time.")
        if (flight.direction == "arrival" and 
            schedule.arrival_time and 
            abs((schedule.arrival_time - arrival_time).total_seconds()) < 300):
            raise HTTPException(status_code=400, detail="Crew already has an arrival around this time.")

    if flight.direction == "arrival":
        #checking if at least one departure was assigned before
        departures_today = []
        for schedule in schedules_today:
            schedule_flight = db.query(models.Flight).filter(
                models.Flight.id == schedule.flight_id, 
                models.Flight.direction == "departure"
            ).first()
            if schedule_flight:
                departures_today.append(schedule)
        
        if not departures_today:
            raise HTTPException(
                status_code=400, 
                detail="Arrival flight cannot be assigned before a departure on the same day."
            )

        latest_departure = max(departures_today, key=lambda x: x.departure_time)
        min_arrival_time = latest_departure.departure_time + timedelta(hours=1)
        if arrival_time < min_arrival_time:
            raise HTTPException(
                status_code=400, 
                detail="Arrival is unrealistically soon after departure."
            )

# def calculate_flight_duration(departure_iso: str, arrival_iso: str) -> int | None:
#     """Legacy function for backward compatibility"""
#     try:
#         dep = datetime.fromisoformat(departure_iso.replace("Z", "+00:00"))
#         arr = datetime.fromisoformat(arrival_iso.replace("Z", "+00:00"))
        
#         if dep and arr:
#             duration_sec = (arr - dep).total_seconds()
#             return int(duration_sec // 60)
#         return None
#     except Exception:
#         return None