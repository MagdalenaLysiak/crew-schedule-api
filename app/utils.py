import requests
import re
import os
from datetime import datetime, timedelta, timezone
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo
from app import models
from .data_structures import DurationResult
from .config import ApiConfig, COUNTRY_TIMEZONES
from .logger_service import LoggerService
from sqlalchemy.orm import Session
from sqlalchemy import func
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
api_config = ApiConfig()
logger = LoggerService(__name__)

try:
    import pytz
    import pycountry
    HAS_TIMEZONE_LIBS = True
except ImportError:
    HAS_TIMEZONE_LIBS = False
    logger.warning("pytz and pycountry not available")


def get_gmt_offset_from_country(country: str) -> str:
    try:
        if country in COUNTRY_TIMEZONES:
            tz_name = COUNTRY_TIMEZONES[country]

            if HAS_TIMEZONE_LIBS:
                tz = pytz.timezone(tz_name)
                now = datetime.now(tz)
                offset = now.utcoffset()
            else:
                tz = ZoneInfo(tz_name)
                now = datetime.now(tz)
                offset = now.utcoffset()

            if offset:
                total_seconds = int(offset.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                sign = "+" if hours >= 0 else "-"
                if minutes == 0:
                    return f"GMT{sign}{abs(hours)}"
                else:
                    return f"GMT{sign}{abs(hours)}:{minutes:02d}"

        return "GMT+0"

    except Exception as e:
        logger.warning(f"Failed to get GMT offset for {country}: {e}")
        return "GMT+0"


def get_airport_country(iata_code: str) -> str:
    try:
        # free airport API
        url = f"https://api.api-ninjas.com/v1/airports?iata={iata_code}"
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return data[0].get('country', '')

    except Exception as e:
        logger.warning(f"Failed to get country for airport {iata_code}: {e}")

    return ""


def get_timezone_from_iata(iata_code: str) -> str:
    try:
        country = get_airport_country(iata_code)
        if country:
            return get_gmt_offset_from_country(country)

    except Exception as e:
        logger.warning(f"Failed to get timezone for {iata_code}: {e}")

    return "GMT+0"


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
        logger.error(f"Failed to resolve GMT offset for '{tz_name}': {e}")
        return "GMT+0"


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
    origin_gmt_offset: str = None,
    destination_gmt_offset: str = None,
    origin_iata: str = None,
    destination_iata: str = None
) -> DurationResult:
    if not dep_time or not arr_time:
        return DurationResult(0, "0h 0m", False)

    try:
        if dep_time.tzinfo is None and origin_gmt_offset:
            offset_hours = parse_gmt_offset(origin_gmt_offset)
            dep_tz = timezone(timedelta(hours=offset_hours))
            dep_time = dep_time.replace(tzinfo=dep_tz)
        elif dep_time.tzinfo is None:
            dep_time = dep_time.replace(tzinfo=timezone.utc)

        if arr_time.tzinfo is None and destination_gmt_offset:
            offset_hours = parse_gmt_offset(destination_gmt_offset)
            arr_tz = timezone(timedelta(hours=offset_hours))
            arr_time = arr_time.replace(tzinfo=arr_tz)
        elif arr_time.tzinfo is None:
            arr_time = arr_time.replace(tzinfo=timezone.utc)

        duration_td = arr_time - dep_time

        if duration_td.total_seconds() <= 0:
            duration_td += timedelta(days=1)
        elif duration_td.total_seconds() < 60 * 60:  # less than 1h
            if origin_gmt_offset and destination_gmt_offset:
                origin_hours = parse_gmt_offset(origin_gmt_offset)
                dest_hours = parse_gmt_offset(destination_gmt_offset)

                if origin_hours != dest_hours:
                    timezone_diff_hours = abs(origin_hours - dest_hours)
                    duration_td = timedelta(hours=timezone_diff_hours) + duration_td

        duration_minutes = int(duration_td.total_seconds() // 60)

        if duration_minutes <= 0:
            return DurationResult(0, "0h 0m", False)
        if duration_minutes > 20 * 60:
            return DurationResult(0, "0h 0m", False)

        hours = duration_minutes // 60
        minutes = duration_minutes % 60
        duration_text = f"{hours}h {minutes}m"

        return DurationResult(duration_minutes, duration_text, True)

    except Exception as e:
        logger.error(f"[DURATION] Calculation error: {e}")
        return DurationResult(0, "0h 0m", False)


def fetch_arrivals_by_airport(airport_iata: str, date_from: str = None, date_to: str = None):
    params = {
        "access_key": API_KEY,
        "arr_iata": airport_iata,
    }

    try:
        resp = requests.get(api_config.base_url, params=params)
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

    try:
        resp = requests.get(api_config.base_url, params=params)
        resp.raise_for_status()
        data = resp.json()

        if "data" not in data:
            raise Exception(f"Unexpected response format: {data}")

        return data["data"]
    except requests.RequestException as e:
        raise Exception(f"API request failed: {e}")


def get_luton_flights(flight_date: str = None):
    return {
        "arrivals": fetch_arrivals_by_airport(api_config.airport_code, date_from=flight_date),
        "departures": fetch_departures_by_airport(api_config.airport_code, date_from=flight_date)
    }


def store_luton_flights(db: Session, flight_date: str = None):
    flights = get_luton_flights(flight_date=flight_date)

    def process_flight_record(flight, direction):
        departure_data = flight.get("departure", {})
        arrival_data = flight.get("arrival", {})
        flight_info = flight.get("flight", {})
        flight_number = flight_info.get("iata") or flight_info.get("icao")

        if not flight_number:
            logger.warning(f"Skipping flight - no flight number: {flight_info}")
            return

        logger.info(f"Processing {direction} flight {flight_number}")
        logger.debug(f"Route: {departure_data.get('iata')} → {arrival_data.get('iata')}")

        dep_timezone = departure_data.get("timezone")
        arr_timezone = arrival_data.get("timezone")

        logger.debug(f"Raw timezones from API: dep='{dep_timezone}', arr='{arr_timezone}'")

        dep_scheduled = departure_data.get("scheduled")
        arr_scheduled = arrival_data.get("scheduled")

        if not dep_scheduled or not arr_scheduled:
            logger.warning(f"Skipping {flight_number} - missing scheduled time data: dep={dep_scheduled}, arr={arr_scheduled}")
            return

        dep_scheduled_raw = datetime.fromisoformat(dep_scheduled.replace("Z", "+00:00")).replace(tzinfo=None)
        arr_scheduled_raw = datetime.fromisoformat(arr_scheduled.replace("Z", "+00:00")).replace(tzinfo=None)

        origin_iata = departure_data.get("iata")
        destination_iata = arrival_data.get("iata")
        dep_gmt_offset = "GMT+0"
        arr_gmt_offset = "GMT+0"

        if dep_timezone:
            try:
                dep_gmt_offset = get_gmt_offset_from_timezone(dep_timezone)
            except Exception:
                pass
        if dep_gmt_offset == "GMT+0" and origin_iata:
            dep_gmt_offset = get_timezone_from_iata(origin_iata)

        if arr_timezone:
            try:
                arr_gmt_offset = get_gmt_offset_from_timezone(arr_timezone)
            except Exception:
                pass
        if arr_gmt_offset == "GMT+0" and destination_iata:
            arr_gmt_offset = get_timezone_from_iata(destination_iata)

        duration_result = calculate_timezone_adjusted_duration(
            dep_scheduled_raw, arr_scheduled_raw, dep_gmt_offset, arr_gmt_offset, origin_iata, destination_iata
        )

        # basic time difference calc fallback
        if not duration_result.is_valid:
            try:
                raw_diff = arr_scheduled_raw - dep_scheduled_raw
                if raw_diff.total_seconds() < 0:
                    raw_diff += timedelta(days=1)

                duration_minutes = int(raw_diff.total_seconds() // 60)
                if 0 < duration_minutes <= 12 * 60:
                    hours = duration_minutes // 60
                    minutes = duration_minutes % 60
                    duration_result = DurationResult(duration_minutes, f"{hours}h {minutes}m", True)
                    logger.info(f"Using raw time difference for {flight_number}: {duration_result.text}")
            except Exception as e:
                logger.error(f"All duration calculations failed for {flight_number}: {e}")

        if not duration_result.is_valid:
            logger.warning(f"Skipping {flight_number} - Could not calculate valid duration")
            return

        if duration_result.minutes > 12 * 60:
            logger.warning(f"Skipping {flight_number} - Duration too long: {duration_result.minutes} minutes")
            return

        today_local = datetime.now().date()
        if dep_scheduled_raw.date() != today_local:
            logger.info(f"Skipping flight {flight_number} - not from today")
            return

        existing = db.query(models.Flight).filter(
            models.Flight.flight_number == flight_number,
            models.Flight.direction == direction,
            func.date(models.Flight.departure_time) == today_local
        ).first()

        if not existing:
            logger.info(f"Storing: {duration_result.text} ({origin_iata} {dep_gmt_offset} → {destination_iata} {arr_gmt_offset})")

            db_flight = models.Flight(
                flight_number=flight_number,
                origin=origin_iata,
                destination=destination_iata,
                direction=direction,
                duration_minutes=duration_result.minutes,
                duration_text=duration_result.text,
                departure_time=dep_scheduled_raw,
                arrival_time=arr_scheduled_raw,
                scheduled_departure_time=dep_scheduled_raw,
                scheduled_arrival_time=arr_scheduled_raw,
                origin_timezone=dep_timezone or "UTC",
                destination_timezone=arr_timezone or "UTC",
                origin_gmt_offset=dep_gmt_offset,
                destination_gmt_offset=arr_gmt_offset
            )
            db.add(db_flight)
        else:
            logger.debug("Flight already exists in database")

    logger.info(f"Processing {len(flights['arrivals'])} arrivals...")
    for flight in flights["arrivals"]:
        process_flight_record(flight, "arrival")

    logger.info(f"Processing {len(flights['departures'])} departures...")
    for flight in flights["departures"]:
        process_flight_record(flight, "departure")

    db.commit()
    logger.info("All flights committed to database")
