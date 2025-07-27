from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from app import models
from typing import List, Optional

MINIMUM_BUFFER_HOURS = 3
DUTY_TIME_LIMIT_HOURS = 14
MAX_FLIGHTS_PER_DAY = 2

class FlightConflict:
    """scheduling conflict between flights"""
    def __init__(self, conflicting_flight: models.CrewSchedule, conflict_type: str, 
                 time_gap: timedelta, required_buffer: timedelta):
        self.conflicting_flight = conflicting_flight
        self.conflict_type = conflict_type
        self.time_gap = time_gap
        self.required_buffer = required_buffer
        
    def __str__(self):
        gap_hours = self.time_gap.total_seconds() / 3600
        buffer_hours = self.required_buffer.total_seconds() / 3600
        return (f"{self.conflict_type}: Gap of {gap_hours:.1f}h is less than required "
                f"{buffer_hours:.1f}h buffer with flight {self.conflicting_flight.flight_number}")

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
    """
    target_date = departure_time.date()
    
    print(f"New flight: {new_flight.flight_number} ({new_flight.direction})")
    print(f"Route: {new_flight.origin} → {new_flight.destination}")
    print(f"Date: {target_date}")
    
    existing_flights = db.query(models.CrewSchedule).filter(
        models.CrewSchedule.crew_id == crew_id,
        func.date(models.CrewSchedule.departure_time) == target_date
    ).all()
    
    luton_departures = []
    luton_arrivals = []
    
    for flight in existing_flights:
        flight_record = db.query(models.Flight).filter(
            models.Flight.flight_number == flight.flight_number,
            func.date(models.Flight.departure_time) == target_date
        ).first()
        
        if flight_record:
            if flight_record.direction == "departure" and flight_record.origin == "LTN":
                luton_departures.append(flight)
                print(f"Found existing departure: {flight.flight_number}")
            elif flight_record.direction == "arrival" and flight_record.destination == "LTN":
                luton_arrivals.append(flight)
                print(f"Found existing arrival: {flight.flight_number}")
    
    is_luton_departure = (new_flight.direction == "departure" and new_flight.origin == "LTN")
    is_luton_arrival = (new_flight.direction == "arrival" and new_flight.destination == "LTN")
    
    print(f"New flight is Luton departure: {is_luton_departure}")
    print(f"New flight is Luton arrival: {is_luton_arrival}")
    
    if is_luton_departure and len(luton_departures) >= 1:
        existing_dep = luton_departures[0]
        raise HTTPException(
            status_code=400,
            detail=f"Crew member already has a departure flight from Luton on {target_date}: "
                   f"{existing_dep.flight_number} at {existing_dep.departure_time.strftime('%H:%M')}. "
                   f"Only one departure per day is allowed."
        )

    if is_luton_arrival and len(luton_arrivals) >= 1:
        existing_arr = luton_arrivals[0]
        raise HTTPException(
            status_code=400,
            detail=f"Crew member already has an arrival flight to Luton on {target_date}: "
                   f"{existing_arr.flight_number} at {existing_arr.arrival_time.strftime('%H:%M')}. "
                   f"Only one arrival per day is allowed."
        )

    if is_luton_departure and len(luton_arrivals) > 0:
        existing_arrival = luton_arrivals[0]
        if departure_time >= existing_arrival.departure_time:
            raise HTTPException(
                status_code=400,
                detail=f"Chosen departure flight {new_flight.flight_number} at {departure_time.strftime('%H:%M')} "
                       f"is scheduled before crew's booked arrival flight {existing_arrival.flight_number} "
                       f"at {existing_arrival.departure_time.strftime('%H:%M')} on the same day."
            )
    
    if is_luton_arrival and len(luton_departures) > 0:
        existing_departure = luton_departures[0]
        if departure_time <= existing_departure.arrival_time:
            raise HTTPException(
                status_code=400,
                detail=f"Chosen arrival flight {new_flight.flight_number} at {departure_time.strftime('%H:%M')} "
                       f"is scheduled after crew's booked departure flight {existing_departure.flight_number} "
                       f"lands at {existing_departure.arrival_time.strftime('%H:%M')} on the same day."
            )
    
    print(f"Flight sequence validation passed")

def flight_assignment_validation(
    db: Session,
    crew_id: int,
    new_flight: models.Flight,
    departure_time: datetime,
    arrival_time: datetime,
    buffer_hours: float = MINIMUM_BUFFER_HOURS
) -> None:
    """
    Flight assignment validation checking:
    """
    
    buffer_delta = timedelta(hours=buffer_hours)
    target_date = departure_time.date()
    
    print(f"Flight: {new_flight.flight_number} ({new_flight.direction})")
    print(f"Time: {departure_time.strftime('%H:%M')} → {arrival_time.strftime('%H:%M')}")
    
    existing_assignment = db.query(models.CrewSchedule).filter(
        models.CrewSchedule.crew_id == crew_id,
        models.CrewSchedule.flight_number == new_flight.flight_number,
        func.date(models.CrewSchedule.departure_time) == target_date
    ).first()
    
    if existing_assignment:
        raise HTTPException(
            status_code=400, 
            detail=f"Crew member is already assigned to flight {new_flight.flight_number}"
        )
    
    validate_luton_flight_sequence(db, crew_id, new_flight, departure_time, arrival_time)
    
    date_range_start = target_date - timedelta(days=1)
    date_range_end = target_date + timedelta(days=1)
    
    existing_flights = db.query(models.CrewSchedule).filter(
        models.CrewSchedule.crew_id == crew_id,
        func.date(models.CrewSchedule.departure_time) >= date_range_start,
        func.date(models.CrewSchedule.departure_time) <= date_range_end
    ).order_by(models.CrewSchedule.departure_time).all()
    
    daily_flights = [f for f in existing_flights if f.departure_time.date() == target_date]
    
    print(f"Found {len(daily_flights)} flights on target date")
    
    if len(daily_flights) >= MAX_FLIGHTS_PER_DAY:
        raise HTTPException(
            status_code=400,
            detail=f"Crew member already has {MAX_FLIGHTS_PER_DAY} flights scheduled on {target_date}. "
                   f"Maximum allowed: 1 departure + 1 arrival per day."
        )
    
    conflicts = []
    
    for existing_flight in existing_flights:
        if existing_flight.arrival_time <= existing_flight.departure_time:
            print(f"WARNING: Invalid existing flight data!")
            continue
            
        conflict = check_flight_time_conflict(
            existing_flight, departure_time, arrival_time, buffer_delta
        )
        if conflict:
            conflicts.append(conflict)
            print(f"Time conflict detected: {conflict}")
    
    if conflicts:
        conflict_details = "; ".join(str(c) for c in conflicts)
        raise HTTPException(
            status_code=400,
            detail=f"Flight assignment conflicts detected: {conflict_details}"
        )
    
    crew = db.query(models.CrewMember).filter(models.CrewMember.id == crew_id).first()
    if not crew:
        raise HTTPException(status_code=404, detail="Crew member not found")
    
    validate_crew_limits_per_flight(db, new_flight, crew.role)
    
    print(f"All validation checks passed!")

def check_flight_time_conflict(
    existing_flight: models.CrewSchedule,
    new_departure: datetime,
    new_arrival: datetime,
    buffer_delta: timedelta
) -> Optional[FlightConflict]:
    """
    check if a new flight conflicts with an existing flight assignment.
    """
    
    existing_dep = existing_flight.departure_time
    existing_arr = existing_flight.arrival_time
    
    print(f"[CONFLICT_CHECK] Existing: {existing_dep.strftime('%m/%d %H:%M')} → {existing_arr.strftime('%m/%d %H:%M')}")
    print(f"[CONFLICT_CHECK] New: {new_departure.strftime('%m/%d %H:%M')} → {new_arrival.strftime('%m/%d %H:%M')}")
    
    if new_departure > existing_arr:
        gap = new_departure - existing_arr
        if gap < buffer_delta:
            return FlightConflict(
                existing_flight, 
                "departure_too_close_after_arrival",
                gap, 
                buffer_delta
            )
    
    if new_arrival < existing_dep:
        gap = existing_dep - new_arrival
        if gap < buffer_delta:
            return FlightConflict(
                existing_flight,
                "arrival_too_close_before_departure", 
                gap,
                buffer_delta
            )
    
    if (new_departure < existing_arr and new_arrival > existing_dep):
        overlap_start = max(new_departure, existing_dep)
        overlap_end = min(new_arrival, existing_arr)
        overlap_duration = overlap_end - overlap_start
        
        return FlightConflict(
            existing_flight,
            "flights_overlap",
            overlap_duration,
            buffer_delta
        )
    
    return None

def validate_crew_limits_per_flight(db: Session, flight: models.Flight, crew_role: str) -> None:
    """validate that flight doesn't exceed crew limits (2 pilots, 4 flight attendants)"""
    
    assignments_for_flight = db.query(models.FlightAssignment).join(
        models.CrewMember
    ).filter(
        models.FlightAssignment.flight_number == flight.flight_number,
        func.date(models.FlightAssignment.departure_time) == flight.departure_time.date()
    ).all()
    
    pilots = sum(1 for a in assignments_for_flight 
                if db.query(models.CrewMember).filter(models.CrewMember.id == a.crew_id).first().role.lower() == "pilot")
    attendants = sum(1 for a in assignments_for_flight 
                    if db.query(models.CrewMember).filter(models.CrewMember.id == a.crew_id).first().role.lower() == "flight attendant")
    
    role_lower = crew_role.lower()
    if role_lower == "pilot" and pilots >= 2:
        raise HTTPException(
            status_code=400, 
            detail=f"Flight {flight.flight_number} already has 2 pilots assigned"
        )
    elif role_lower == "flight attendant" and attendants >= 4:
        raise HTTPException(
            status_code=400, 
            detail=f"Flight {flight.flight_number} already has 4 flight attendants assigned"
        )

def get_crew_schedule_summary(db: Session, crew_id: int, date: datetime.date) -> dict:
    """
    Get a summary of crew member's schedule for a specific date
    """
    
    flights = db.query(models.CrewSchedule).filter(
        models.CrewSchedule.crew_id == crew_id,
        func.date(models.CrewSchedule.departure_time) == date
    ).order_by(models.CrewSchedule.departure_time).all()
    
    if not flights:
        return {"date": date.isoformat(), "flights": [], "total_duty_time": "0h 0m"}
    
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
        "within_limits": duty_hours <= DUTY_TIME_LIMIT_HOURS
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
        db, crew_id, flight, departure_time, arrival_time, MINIMUM_BUFFER_HOURS
    )