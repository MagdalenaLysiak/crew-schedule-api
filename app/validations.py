from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from app import models
from app.config import BusinessRules, ApiConfig
from app.logger_service import LoggerService
from typing import Optional

business_rules = BusinessRules()
api_config = ApiConfig()
logger = LoggerService(__name__)


class FlightConflict:
    def __init__(self, conflicting_assignment: models.FlightAssignment, conflict_type: str,
                 time_gap: timedelta, required_buffer: timedelta):
        self.conflicting_assignment = conflicting_assignment
        self.conflict_type = conflict_type
        self.time_gap = time_gap
        self.required_buffer = required_buffer

    def __str__(self):
        gap_hours = self.time_gap.total_seconds() / 3600
        buffer_hours = self.required_buffer.total_seconds() / 3600
        flight_number = self.conflicting_assignment.flight.flight_number
        return (f"{self.conflict_type}: Gap of {gap_hours:.1f}h is less than required "
                f"{buffer_hours:.1f}h buffer with flight {flight_number}")


def validate_luton_flight_sequence(
    db: Session,
    crew_id: int,
    new_flight: models.Flight,
    departure_time: datetime,
    arrival_time: datetime
) -> None:
    """
    validate specific flight rules:
    1. only one departure flight per day (crew leaving Luton)
    2. only one arrival flight per day (crew returning to Luton)  
    3. departure must come before arrival on the same day
    4. 3h time buffer between flights
    5. arrival flight origin must match departure flight destination (same day)
    """
    target_date = departure_time.date()

    logger.info(f"New flight: {new_flight.flight_number} ({new_flight.direction})")
    logger.debug(f"Route: {new_flight.origin} → {new_flight.destination}")
    logger.debug(f"Date: {target_date}")

    existing_assignments = db.query(models.FlightAssignment).join(
        models.Flight
    ).filter(
        models.FlightAssignment.crew_id == crew_id,
        models.FlightAssignment.status == "active",
        func.date(models.Flight.departure_time) == target_date
    ).all()

    luton_departures = []
    luton_arrivals = []

    for assignment in existing_assignments:
        flight = assignment.flight
        if flight.direction == "departure" and flight.origin == api_config.airport_code:
            luton_departures.append(assignment)
            logger.debug(f"Found existing departure: {flight.flight_number} ({api_config.airport_code} → {flight.destination})")
        elif flight.direction == "arrival" and flight.destination == api_config.airport_code:
            luton_arrivals.append(assignment)
            logger.debug(f"Found existing arrival: {flight.flight_number} ({flight.origin} → {api_config.airport_code})")

    is_luton_departure = (new_flight.direction == "departure" and new_flight.origin == api_config.airport_code)
    is_luton_arrival = (new_flight.direction == "arrival" and new_flight.destination == api_config.airport_code)

    logger.debug(f"New flight is Luton departure: {is_luton_departure}")
    logger.debug(f"New flight is Luton arrival: {is_luton_arrival}")

    if is_luton_departure and len(luton_departures) >= 1:
        existing_assignment = luton_departures[0]
        existing_flight = existing_assignment.flight
        raise HTTPException(
            status_code=409,
            detail=f"Crew member already has a departure flight from Luton on {target_date}: "
                   f"{existing_flight.flight_number} at {existing_flight.departure_time.strftime('%H:%M')}. "
                   f"Only one departure per day is allowed."
        )

    if is_luton_arrival and len(luton_arrivals) >= 1:
        existing_assignment = luton_arrivals[0]
        existing_flight = existing_assignment.flight
        raise HTTPException(
            status_code=409,
            detail=f"Crew member already has an arrival flight to Luton on {target_date}: "
                   f"{existing_flight.flight_number} at {existing_flight.arrival_time.strftime('%H:%M')}. "
                   f"Only one arrival per day is allowed."
        )

    if is_luton_arrival and len(luton_departures) > 0:
        existing_departure = luton_departures[0]
        departure_flight = existing_departure.flight

        if new_flight.origin != departure_flight.destination:
            raise HTTPException(
                status_code=409,
                detail=f"Arrival flight {new_flight.flight_number} origin ({new_flight.origin}) "
                       f"must match the destination of departure flight {departure_flight.flight_number} "
                       f"({departure_flight.destination}) on the same day. "
                       f"Crew must return from the same location they departed to."
            )

        logger.debug(f"Origin-destination match validated: {new_flight.origin} matches {departure_flight.destination}")

    if is_luton_departure and len(luton_arrivals) > 0:
        existing_arrival = luton_arrivals[0]
        arrival_flight = existing_arrival.flight

        if new_flight.destination != arrival_flight.origin:
            raise HTTPException(
                status_code=409,
                detail=f"Departure flight {new_flight.flight_number} destination ({new_flight.destination}) "
                       f"must match the origin of arrival flight {arrival_flight.flight_number} "
                       f"({arrival_flight.origin}) on the same day. "
                       f"Crew must depart to the same location they will return from."
            )

        logger.debug(f"Destination-origin match validated: {new_flight.destination} matches {arrival_flight.origin}")

    if is_luton_departure and len(luton_arrivals) > 0:
        existing_assignment = luton_arrivals[0]
        existing_flight = existing_assignment.flight
        if departure_time >= existing_flight.departure_time:
            raise HTTPException(
                status_code=409,
                detail=f"Departure flight {new_flight.flight_number} at {departure_time.strftime('%H:%M')} "
                       f"must be scheduled before arrival flight {existing_flight.flight_number} "
                       f"at {existing_flight.departure_time.strftime('%H:%M')} on the same day."
            )

    if is_luton_arrival and len(luton_departures) > 0:
        existing_assignment = luton_departures[0]
        existing_flight = existing_assignment.flight
        if departure_time <= existing_flight.arrival_time:
            raise HTTPException(
                status_code=409,
                detail=f"Arrival flight {new_flight.flight_number} at {departure_time.strftime('%H:%M')} "
                       f"must be scheduled after departure flight {existing_flight.flight_number} "
                       f"lands at {existing_flight.arrival_time.strftime('%H:%M')} on the same day."
            )


def flight_assignment_validation(
    db: Session,
    crew_id: int,
    new_flight: models.Flight,
    departure_time: datetime,
    arrival_time: datetime,
    buffer_hours: float = None
) -> None:

    if buffer_hours is None:
        buffer_hours = business_rules.buffer_hours
    buffer_delta = timedelta(hours=buffer_hours)
    target_date = departure_time.date()

    logger.info(f"Flight: {new_flight.flight_number} ({new_flight.direction})")
    logger.debug(f"Time: {departure_time.strftime('%H:%M')} → {arrival_time.strftime('%H:%M')}")

    existing_assignment = db.query(models.FlightAssignment).filter(
        models.FlightAssignment.crew_id == crew_id,
        models.FlightAssignment.flight_id == new_flight.id,
        models.FlightAssignment.status == "active"
    ).first()

    if existing_assignment:
        raise HTTPException(
            status_code=409,
            detail=f"Crew member is already assigned to flight {new_flight.flight_number}"
        )

    validate_luton_flight_sequence(db, crew_id, new_flight, departure_time, arrival_time)

    date_range_start = target_date - timedelta(days=1)
    date_range_end = target_date + timedelta(days=1)

    existing_assignments = db.query(models.FlightAssignment).join(
        models.Flight
    ).filter(
        models.FlightAssignment.crew_id == crew_id,
        models.FlightAssignment.status == "active",
        func.date(models.Flight.departure_time) >= date_range_start,
        func.date(models.Flight.departure_time) <= date_range_end
    ).order_by(models.Flight.departure_time).all()

    daily_assignments = [a for a in existing_assignments
                         if a.flight.departure_time.date() == target_date]

    logger.debug(f"Found {len(daily_assignments)} flights on target date")

    if len(daily_assignments) >= business_rules.max_flights_per_day:
        raise HTTPException(
            status_code=409,
            detail=f"Crew member already has {business_rules.max_flights_per_day} flights scheduled on {target_date}. "
                   f"Maximum allowed: 1 departure + 1 arrival per day."
        )

    conflicts = []

    for assignment in existing_assignments:
        flight = assignment.flight
        if flight.arrival_time <= flight.departure_time:
            logger.warning(f"Invalid existing flight data for {flight.flight_number}!")
            continue

        conflict = check_flight_time_conflict(
            assignment, departure_time, arrival_time, buffer_delta
        )
        if conflict:
            conflicts.append(conflict)
            logger.warning(f"Time conflict detected: {conflict}")

    if conflicts:
        conflict_details = "; ".join(str(c) for c in conflicts)
        raise HTTPException(
            status_code=409,
            detail=f"Flight assignment conflicts detected: {conflict_details}"
        )

    crew = db.query(models.CrewMember).filter(models.CrewMember.id == crew_id).first()
    if not crew:
        raise HTTPException(status_code=404, detail="Crew member not found")
    
    if crew.is_on_leave:
        raise HTTPException(
            status_code=409,
            detail=f"Crew member {crew.name} is currently on leave and cannot be assigned to flights"
        )

    validate_crew_limits_per_flight(db, new_flight, crew.role)


def check_flight_time_conflict(
    existing_assignment: models.FlightAssignment,
    new_departure: datetime,
    new_arrival: datetime,
    buffer_delta: timedelta
) -> Optional[FlightConflict]:

    existing_flight = existing_assignment.flight
    existing_dep = existing_flight.departure_time
    existing_arr = existing_flight.arrival_time

    logger.debug(f"[CONFLICT_CHECK] Existing: {existing_dep.strftime('%m/%d %H:%M')} → {existing_arr.strftime('%m/%d %H:%M')}")
    logger.debug(f"[CONFLICT_CHECK] New: {new_departure.strftime('%m/%d %H:%M')} → {new_arrival.strftime('%m/%d %H:%M')}")

    if new_departure > existing_arr:
        gap = new_departure - existing_arr
        if gap < buffer_delta:
            return FlightConflict(
                existing_assignment,
                "departure_too_close_after_arrival",
                gap,
                buffer_delta
            )

    if new_arrival < existing_dep:
        gap = existing_dep - new_arrival
        if gap < buffer_delta:
            return FlightConflict(
                existing_assignment,
                "arrival_too_close_before_departure", 
                gap,
                buffer_delta
            )

    if (new_departure < existing_arr and new_arrival > existing_dep):
        overlap_start = max(new_departure, existing_dep)
        overlap_end = min(new_arrival, existing_arr)
        overlap_duration = overlap_end - overlap_start

        return FlightConflict(
            existing_assignment,
            "flights_overlap",
            overlap_duration,
            buffer_delta
        )

    return None


def validate_crew_limits_per_flight(db: Session, flight: models.Flight, crew_role: str) -> None:
    assignments_for_flight = db.query(models.FlightAssignment).join(
        models.CrewMember
    ).filter(
        models.FlightAssignment.flight_id == flight.id,
        models.FlightAssignment.status == "active"
    ).all()

    pilots = sum(1 for a in assignments_for_flight
                 if a.crew_member.role.lower() == "pilot")
    attendants = sum(1 for a in assignments_for_flight
                     if a.crew_member.role.lower() == "flight attendant")

    role_lower = crew_role.lower()
    if role_lower == "pilot" and pilots >= business_rules.max_pilots_per_flight:
        raise HTTPException(
            status_code=409,
            detail=f"Flight {flight.flight_number} already has {business_rules.max_pilots_per_flight} pilots assigned"
        )
    elif role_lower == "flight attendant" and attendants >= business_rules.max_attendants_per_flight:
        raise HTTPException(
            status_code=409,
            detail=f"Flight {flight.flight_number} already has {business_rules.max_attendants_per_flight} flight attendants assigned"
        )


def get_crew_schedule_summary(db: Session, crew_id: int, date: datetime.date) -> dict:
    assignments = db.query(models.FlightAssignment).join(
        models.Flight
    ).filter(
        models.FlightAssignment.crew_id == crew_id,
        models.FlightAssignment.status == "active",
        func.date(models.Flight.departure_time) == date
    ).order_by(models.Flight.departure_time).all()

    if not assignments:
        return {"date": date.isoformat(), "flights": [], "total_duty_time": "0h 0m"}

    flights = [assignment.flight for assignment in assignments]
    first_departure = flights[0].departure_time
    last_arrival = flights[-1].arrival_time

    duty_start = first_departure - timedelta(hours=1)
    duty_end = last_arrival + timedelta(hours=0.5)

    total_duty = duty_end - duty_start
    duty_hours = int(total_duty.total_seconds() // 3600)
    duty_minutes = int((total_duty.total_seconds() % 3600) // 60)

    schedule_summary = {
        "date": date.isoformat(),
        "flights": [
            {
                "flight_number": f.flight_number,
                "departure": f.departure_time.strftime("%H:%M"),
                "arrival": f.arrival_time.strftime("%H:%M"),
                "route": f"{f.origin} → {f.destination}",
                "duration": f.duration_text or f"{((f.arrival_time - f.departure_time).total_seconds() // 3600):.0f}h {(((f.arrival_time - f.departure_time).total_seconds() % 3600) // 60):.0f}m"
            }
            for f in flights
        ],
        "total_flights": len(flights),
        "duty_start": duty_start.strftime("%H:%M"),
        "duty_end": duty_end.strftime("%H:%M"),
        "total_duty_time": f"{duty_hours}h {duty_minutes}m",
        "within_limits": duty_hours <= business_rules.duty_time_limit_hours
    }

    return schedule_summary


def validate_flight_assignment(
    db: Session,
    crew_id: int,
    flight: models.Flight,
    departure_time: datetime,
    arrival_time: datetime
) -> None:
    flight_assignment_validation(
        db, crew_id, flight, departure_time, arrival_time
    )
