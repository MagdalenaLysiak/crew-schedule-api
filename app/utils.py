import requests
import re
import os
from datetime import datetime, timedelta, timezone
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo
from app import models
from sqlalchemy.orm import Session
from sqlalchemy import func
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
BASE_URL = "http://api.aviationstack.com/v1/flights"


def get_gmt_offset_from_timezone(tz_name: str, ref_time: datetime = None) -> str:
    try:
        ref_time = ref_time or datetime.utcnow()
        tz = ZoneInfo(tz_name)
        local_time = ref_time.astimezone(tz)
        offset = local_time.utcoffset()

        if offset is None:
            return "GMT+0"

        total_minutes = int(offset.total_seconds() // 60)
        hours, minutes = divmod(abs(total_minutes), 60)
        sign = "+" if total_minutes >= 0 else "-"
        return f"GMT{sign}{hours}" if minutes == 0 else f"GMT{sign}{hours}:{minutes:02d}"
    except Exception as e:
        print(f"[ERROR] Failed to resolve GMT offset for '{tz_name}': {e}")
        return "GMT+0"


def parse_aviationstack_timestamp(timestamp: str, timezone_name: str = None):
    if not timestamp:
        return None, None, None

    try:
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


def parse_gmt_offset(offset_str):
    if not offset_str or not offset_str.startswith("GMT"):
        return 0.0

    match = re.match(r"GMT([+-])(\d+)(?::(\d+))?", offset_str)
    if not match:
        return 0.0

    sign, hours, minutes = match.groups()
    total_hours = float(hours) + (float(minutes or 0) / 60.0)
    return total_hours if sign == '+' else -total_hours


def calculate_timezone_adjusted_duration(
    dep_time: datetime,
    arr_time: datetime,
    origin_gmt_offset: str,
    destination_gmt_offset: str
):
    """
    Calculate the actual flight duration by converting both times to UTC and calculating the difference
    """
    if not dep_time or not arr_time:
        return 0, "0h 0m"

    try:
        print(f" Departure: {dep_time.strftime('%Y-%m-%d %H:%M')} {origin_gmt_offset}")
        print(f" Arrival: {arr_time.strftime('%Y-%m-%d %H:%M')} {destination_gmt_offset}")

        # GMT to hours
        origin_offset_hours = parse_gmt_offset(origin_gmt_offset)
        dest_offset_hours = parse_gmt_offset(destination_gmt_offset)

        print(f" Origin GMT offset: {origin_offset_hours} hours")
        print(f" Destination GMT offset: {dest_offset_hours} hours")

        # local times to UTC
        dep_utc = dep_time - timedelta(hours=origin_offset_hours)
        arr_utc = arr_time - timedelta(hours=dest_offset_hours)

        # handling cross date flights (if arrival is next day)
        if arr_time.date() > dep_time.date():
            local_duration = arr_time - dep_time
            utc_duration = arr_utc - dep_utc

            local_hours = local_duration.total_seconds() / 3600
            utc_hours = utc_duration.total_seconds() / 3600

            if 5 <= local_hours <= 12 and utc_hours > 20:
                # if too much time added, subtract a day
                arr_utc -= timedelta(days=1)
            elif 5 <= local_hours <= 12 and utc_hours < 3:
                # if too little time, add a day  
                arr_utc += timedelta(days=1)

        print(f" Departure UTC: {dep_utc.strftime('%Y-%m-%d %H:%M')} UTC")
        print(f" Arrival UTC: {arr_utc.strftime('%Y-%m-%d %H:%M')} UTC")

        # actual flight duration in UTC
        actual_duration_minutes = int((arr_utc - dep_utc).total_seconds() // 60)

        print(f" Actual flight duration: {actual_duration_minutes} minutes")

        if actual_duration_minutes <= 0:
            print(f"Invalid duration: {actual_duration_minutes} minutes")
            return 0, "0h 0m"

        # flights shouldn't be longer than 20 hours
        if actual_duration_minutes > 20 * 60:
            print(f"Unrealistic duration: {actual_duration_minutes} minutes (>{actual_duration_minutes//60} hours)")
            return 0, "0h 0m"

        # convert to hours and minutes
        hours = actual_duration_minutes // 60
        minutes = actual_duration_minutes % 60
        duration_text = f"{hours}h {minutes}m"

        print(f" Final result: {duration_text}")

        return actual_duration_minutes, duration_text

    except Exception as e:
        print(f"[DURATION] Error: {e}")
        return 0, "0h 0m"


def calculate_realistic_flight_duration(dep_local: datetime, arr_local: datetime, 
                                       dep_gmt_offset: str, arr_gmt_offset: str):
    return calculate_timezone_adjusted_duration(dep_local, arr_local, dep_gmt_offset, arr_gmt_offset)


def debug_flight_times(flight_data, direction):
    flight_info = flight_data.get("flight", {})
    flight_number = flight_info.get("iata", "UNKNOWN")

    departure_data = flight_data.get("departure", {})
    arrival_data = flight_data.get("arrival", {})

    print(f"DEBUG: {direction.upper()} Flight {flight_number}")
    print(f"Departure: {departure_data.get('iata')} - {departure_data.get('scheduled')} (TZ: {departure_data.get('timezone')})")
    print(f"Arrival: {arrival_data.get('iata')} - {arrival_data.get('scheduled')} (TZ: {arrival_data.get('timezone')})")

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

        print(f"Raw timezones from API: dep='{dep_timezone}', arr='{arr_timezone}'")

        dep_scheduled_time = departure_data.get("scheduled")
        dep_actual_time = departure_data.get("actual")
        arr_scheduled_time = arrival_data.get("scheduled")
        arr_actual_time = arrival_data.get("actual")

        dep_time_to_use = dep_actual_time or dep_scheduled_time
        arr_time_to_use = arr_actual_time or arr_scheduled_time

        if not dep_time_to_use or not arr_time_to_use:
            print("Skipping - missing critical time data")
            return

        # parse UTC timestamps from API
        dep_utc = datetime.fromisoformat(dep_time_to_use.replace("Z", "+00:00"))
        arr_utc = datetime.fromisoformat(arr_time_to_use.replace("Z", "+00:00"))

        if dep_utc.tzinfo is None:
            dep_utc = dep_utc.replace(tzinfo=timezone.utc)
        if arr_utc.tzinfo is None:
            arr_utc = arr_utc.replace(tzinfo=timezone.utc)

        # convert to local timezones and get GMT
        dep_gmt_offset = "GMT+0"
        arr_gmt_offset = "GMT+0"
        dep_parsed = dep_utc
        arr_parsed = arr_utc
        final_dep_timezone = dep_timezone or "UTC"
        final_arr_timezone = arr_timezone or "UTC"

        if dep_timezone:
            try:
                dep_tz = ZoneInfo(dep_timezone)
                dep_parsed = dep_utc.astimezone(dep_tz)
                dep_gmt_offset = get_gmt_offset_from_timezone(dep_timezone, dep_parsed)
                print(f"Departure: {dep_utc.strftime('%H:%M UTC')} → {dep_parsed.strftime('%H:%M')} {dep_gmt_offset}")
            except Exception as e:
                print(f"Failed to convert departure timezone: {e}")
                final_dep_timezone = "UTC"

        if arr_timezone:
            try:
                arr_tz = ZoneInfo(arr_timezone)
                arr_parsed = arr_utc.astimezone(arr_tz)
                arr_gmt_offset = get_gmt_offset_from_timezone(arr_timezone, arr_parsed)
                print(f"Arrival: {arr_utc.strftime('%H:%M UTC')} → {arr_parsed.strftime('%H:%M')} {arr_gmt_offset}")
            except Exception as e:
                print(f"Failed to convert arrival timezone: {e}")
                final_arr_timezone = "UTC"

        dep_utc_check = dep_parsed.astimezone(timezone.utc)
        arr_utc_check = arr_parsed.astimezone(timezone.utc)

        if arr_utc_check <= dep_utc_check:
            print(f"ERROR: Arrival UTC ({arr_utc_check}) ≤ Departure UTC ({dep_utc_check})")
            debug_flight_times(flight, direction)
            return

        duration_min, duration_text = calculate_timezone_adjusted_duration(
            dep_parsed, arr_parsed, dep_gmt_offset, arr_gmt_offset
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
            func.date(models.Flight.departure_time) == dep_parsed.date()
        ).first()

        if not existing:
            print(f"Storing: {duration_text} ({origin_iata} {dep_gmt_offset} → {destination_iata} {arr_gmt_offset})")

            db_flight = models.Flight(
                flight_number=flight_number,
                origin=origin_iata,
                destination=destination_iata,
                direction=direction,
                duration_minutes=duration_min,
                duration_text=duration_text,
                departure_time=dep_parsed,
                arrival_time=arr_parsed,
                origin_timezone=final_dep_timezone,
                destination_timezone=final_arr_timezone,
                origin_gmt_offset=dep_gmt_offset,
                destination_gmt_offset=arr_gmt_offset
            )
            db.add(db_flight)
        else:
            print("Already exists")

    print(f"Processing {len(flights['arrivals'])} arrivals...")
    for flight in flights["arrivals"]:
        process_flight_record(flight, "arrival")

    print(f"Processing {len(flights['departures'])} departures...")
    for flight in flights["departures"]:
        process_flight_record(flight, "departure")

    db.commit()
    print("All flights committed to database")


def recalculate_duration_with_gmt_offset(
    dep_time: datetime,
    arr_time: datetime,
    origin_gmt_offset: str,
    destination_gmt_offset: str
):
    return calculate_timezone_adjusted_duration(dep_time, arr_time, origin_gmt_offset, destination_gmt_offset)