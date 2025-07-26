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
    1. flight assignments duplication 
    2. maximum flights per day limit
    3. time buffers between flights (3 hours)
    4. maximum crew per flight limits
    5. arrivals after departures
    """
    
    buffer_delta = timedelta(hours=buffer_hours)
    target_date = departure_time.date()
    
    print(f"[ENHANCED_VALIDATION] Using enhanced validation function - checking assignment for crew {crew_id} to flight {new_flight.flight_number}")
    print(f"[ENHANCED_VALIDATION] New flight: {departure_time.strftime('%H:%M')} → {arrival_time.strftime('%H:%M')}")
    print(f"[ENHANCED_VALIDATION] Target date: {target_date}")
    
    # 1  duplicates checking
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
    
    # 2  check flights from previous day and next day to catch overnight scenarios
    date_range_start = target_date - timedelta(days=1)
    date_range_end = target_date + timedelta(days=1)
    
    existing_flights = db.query(models.CrewSchedule).filter(
        models.CrewSchedule.crew_id == crew_id,
        func.date(models.CrewSchedule.departure_time) >= date_range_start,
        func.date(models.CrewSchedule.departure_time) <= date_range_end
    ).order_by(models.CrewSchedule.departure_time).all()
    
    print(f"[VALIDATION] Found {len(existing_flights)} existing flights for crew member")
    
    # 3 check daily flight limit
    daily_flights = [f for f in existing_flights if f.departure_time.date() == target_date]
    
    print(f"[ENHANCED_VALIDATION] Found {len(daily_flights)} flights on target date {target_date}")
    print(f"[ENHANCED_VALIDATION] MAX_FLIGHTS_PER_DAY = {MAX_FLIGHTS_PER_DAY}")
    
    if len(daily_flights) >= MAX_FLIGHTS_PER_DAY:
        print(f"[ENHANCED_VALIDATION] DAILY LIMIT EXCEEDED! Crew has {len(daily_flights)} flights, max is {MAX_FLIGHTS_PER_DAY}")
        raise HTTPException(
            status_code=400,
            detail=f"Crew member already has {MAX_FLIGHTS_PER_DAY} flights scheduled on {target_date}. Cannot assign additional flights."
        )
    
    print(f"[ENHANCED_VALIDATION] Daily limit check passed. Proceeding with time conflict checks...")
    
    # 4 check time conflicts with all existing flights
    conflicts = []
    
    for existing_flight in existing_flights:
        # validate the existing flight data
        if existing_flight.arrival_time <= existing_flight.departure_time:
            print(f"[ENHANCED_VALIDATION] WARNING: Invalid existing flight data - arrival before departure!")
            print(f"[ENHANCED_VALIDATION] Flight {existing_flight.flight_number}: {existing_flight.departure_time} → {existing_flight.arrival_time}")
            continue
            
        conflict = check_flight_time_conflict(
            existing_flight, departure_time, arrival_time, buffer_delta
        )
        if conflict:
            conflicts.append(conflict)
            print(f"[ENHANCED_VALIDATION] Conflict detected: {conflict}")
    
    if conflicts:
        conflict_details = "; ".join(str(c) for c in conflicts)
        raise HTTPException(
            status_code=400,
            detail=f"Flight assignment conflicts detected: {conflict_details}"
        )
    
    # 5 check crew limits per flight
    crew = db.query(models.CrewMember).filter(models.CrewMember.id == crew_id).first()
    if not crew:
        raise HTTPException(status_code=404, detail="Crew member not found")
    
    validate_crew_limits_per_flight(db, new_flight, crew.role)
    
    # 6 validate flight sequence logic (departures before arrivals)
    validate_flight_sequence_logic(db, daily_flights, new_flight, departure_time, arrival_time)
    
    print(f"[VALIDATION] All checks passed for crew {crew_id} assignment to flight {new_flight.flight_number}")

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
    
    # 1 new flight departs too soon after existing flight arrives
    if new_departure > existing_arr:
        gap = new_departure - existing_arr
        if gap < buffer_delta:
            return FlightConflict(
                existing_flight, 
                "departure_too_close_after_arrival",
                gap, 
                buffer_delta
            )
    
    # 2 new flight arrives too close to existing flight departure
    if new_arrival < existing_dep:
        gap = existing_dep - new_arrival
        if gap < buffer_delta:
            return FlightConflict(
                existing_flight,
                "arrival_too_close_before_departure", 
                gap,
                buffer_delta
            )
    
    # 3 flights overlap in time
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
    
    # 4 new flight is too close to existing departure
    if abs((new_departure - existing_dep).total_seconds()) < buffer_delta.total_seconds():
        gap = abs(new_departure - existing_dep)
        return FlightConflict(
            existing_flight,
            "departures_too_close",
            gap,
            buffer_delta
        )
    
    # 5 new flight arrival is too close to existing arrival
    if abs((new_arrival - existing_arr).total_seconds()) < buffer_delta.total_seconds():
        gap = abs(new_arrival - existing_arr)
        return FlightConflict(
            existing_flight,
            "arrivals_too_close", 
            gap,
            buffer_delta
        )
    
    return None

def validate_crew_limits_per_flight(db: Session, flight: models.Flight, crew_role: str) -> None:
    """validate that flight doesn't exceed crew limits (2 pilots, 4 flight attendants)"""
    
    assignments_for_flight = db.query(models.FlightAssignment).filter(
        models.FlightAssignment.flight_number == flight.flight_number,
        func.date(models.FlightAssignment.departure_time) == flight.departure_time.date()
    ).all()
    
    pilots = sum(1 for a in assignments_for_flight if a.crew.role.lower() == "pilot")
    attendants = sum(1 for a in assignments_for_flight if a.crew.role.lower() == "flight attendant")
    
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

def validate_flight_sequence_logic(
    db: Session,
    existing_daily_flights: List[models.CrewSchedule],
    new_flight: models.Flight,
) -> None:
    """
    Validate that crew should have departures before arrivals
    """
    if new_flight.direction == "arrival":
        departures_today = [
            f for f in existing_daily_flights 
            if db.query(models.Flight).filter(
                models.Flight.flight_number == f.flight_number,
                models.Flight.direction == "departure"
            ).first()
        ]
        
        if not departures_today:
            print(f"[WARNING] Arrival flight {new_flight.flight_number} assigned without departure on same day")

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
    
    # calculate total duty time
    first_departure = flights[0].departure_time
    last_arrival = flights[-1].arrival_time
    
    #add buffer
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
                "duration": f"{((f.arrival_time - f.departure_time).total_seconds() // 3600):.0f}h {(((f.arrival_time - f.departure_time).total_seconds() % 3600) // 60):.0f}m"
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