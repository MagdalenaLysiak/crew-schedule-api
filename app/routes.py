from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app import models, schemas
from .database import get_db
from .utils import validate_flight_assignment, store_luton_flights

router = APIRouter()

VALID_CREW_ROLES = {"pilot", "flight attendant"}

@router.post("/crew", response_model=schemas.CrewMemberRead)
def create_crew(crew: schemas.CrewMemberCreate, db: Session = Depends(get_db)):
    if crew.role.lower() not in VALID_CREW_ROLES:
        raise HTTPException(status_code=400, detail="Invalid crew role. Must be 'pilot' or 'flight attendant'.")

    db_crew = models.CrewMember(**crew.dict())
    db.add(db_crew)
    db.commit()
    db.refresh(db_crew)
    return db_crew

@router.get("/crew/{crew_id}", response_model=schemas.CrewMemberRead)
def read_crew(crew_id: int, db: Session = Depends(get_db)):
    crew = db.query(models.CrewMember).filter(models.CrewMember.id == crew_id).first()
    if not crew:
        raise HTTPException(status_code=404, detail="Crew member not found")
    return crew

@router.delete("/crew/{crew_id}")
def delete_crew(crew_id: int, db: Session = Depends(get_db)):
    crew = db.query(models.CrewMember).filter(models.CrewMember.id == crew_id).first()
    if not crew:
        raise HTTPException(status_code=404, detail="Crew member not found")
    #delete related schedules and assignments
    db.query(models.CrewSchedule).filter(models.CrewSchedule.crew_id == crew_id).delete()
    db.query(models.FlightAssignment).filter(models.FlightAssignment.crew_id == crew_id).delete()

    db.delete(crew)
    db.commit()
    return {"message": f"Crew member {crew_id} and related records deleted."}

@router.post("/assign-flight/{crew_id}/{flight_id}")
def assign_flight(crew_id: int, flight_id: int, db: Session = Depends(get_db)):
    #get crew
    crew = db.query(models.CrewMember).filter(models.CrewMember.id == crew_id).first()
    if not crew:
        raise HTTPException(status_code=404, detail="Crew member not found")

    #get flight
    flight = db.query(models.Flight).filter(models.Flight.id == flight_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")

    departure_time = flight.departure_time
    arrival_time = flight.arrival_time

    if not departure_time or not arrival_time:
        raise HTTPException(status_code=400, detail="Flight missing departure or arrival time")

    duration_minutes = flight.duration_minutes
    if duration_minutes is None:
        duration_minutes = 0

    validate_flight_assignment(db, crew_id, flight, departure_time, arrival_time)
    #block duplicate assignment to same flight
    already_assigned = db.query(models.CrewSchedule).filter(
        models.CrewSchedule.crew_id == crew_id,
        models.CrewSchedule.flight_number == flight.flight_number
    ).first()
    if already_assigned:
        raise HTTPException(status_code=400, detail="Crew member is already assigned to this flight")
    #limit 2 flights per crew member per day
    daily_assignments = db.query(models.CrewSchedule).filter(
        models.CrewSchedule.crew_id == crew_id,
        func.date(models.CrewSchedule.departure_time) == departure_time.date()
    ).count()

    if daily_assignments >= 2:
        raise HTTPException(
            status_code=400,
            detail="Crew member already has 2 flights scheduled on this day"
        )
    #max 2 pilots, 4 attendants per flight
    role = crew.role.lower()
    assignments_for_flight = db.query(models.FlightAssignment).filter(
        models.FlightAssignment.flight_number == flight.flight_number
    ).all()

    pilots = sum(1 for a in assignments_for_flight if a.crew.role.lower() == "pilot")
    attendants = sum(1 for a in assignments_for_flight if a.crew.role.lower() == "flight attendant")

    if role == "pilot" and pilots >= 2:
        raise HTTPException(status_code=400, detail="This flight already has 2 pilots assigned")
    if role == "flight attendant" and attendants >= 4:
        raise HTTPException(status_code=400, detail="This flight already has 4 flight attendants assigned")

    new_schedule = models.CrewSchedule(
        crew_id=crew_id,
        crew_name=crew.name,
        flight_id=flight.id,
        flight_number=flight.flight_number,
        departure_time=departure_time,
        arrival_time=arrival_time,
    )
    db.add(new_schedule)

    new_assignment = models.FlightAssignment(
        flight_id=flight.id,
        flight_number=flight.flight_number,
        departure=departure_time.strftime("%Y-%m-%d %H:%M"),
        arrival=arrival_time.strftime("%Y-%m-%d %H:%M"),
        departure_time=departure_time,
        arrival_time=arrival_time,
        crew_id=crew_id,
        crew_name=crew.name,
        duration_minutes=duration_minutes
    )
    db.add(new_assignment)

    db.commit()
    db.refresh(new_schedule)
    db.refresh(new_assignment)

    origin_tz_info = f" {flight.origin_gmt_offset}" if flight.origin_gmt_offset else ""
    dest_tz_info = f" {flight.destination_gmt_offset}" if flight.destination_gmt_offset else ""

    return {
        "message": "Flight assigned successfully",
        "schedule_id": new_schedule.id,
        "assignment_id": new_assignment.id,
        "duration_minutes": duration_minutes,
        "duration_text": f"{duration_minutes//60}h {duration_minutes%60}m" if duration_minutes > 0 else "0h 0m",
        "departure_time": departure_time.strftime('%Y-%m-%d %H:%M') + origin_tz_info,
        "arrival_time": arrival_time.strftime('%Y-%m-%d %H:%M') + dest_tz_info,
        "route": f"{flight.origin} → {flight.destination}",
        "timezone_info": {
            "origin_timezone": flight.origin_timezone,
            "destination_timezone": flight.destination_timezone,
            "origin_gmt_offset": flight.origin_gmt_offset,
            "destination_gmt_offset": flight.destination_gmt_offset
        }
    }

@router.delete("/assignment/{assignment_id}")
def delete_assignment(assignment_id: int, db: Session = Depends(get_db)):
    assignment = db.query(models.FlightAssignment).filter(models.FlightAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    #delete related crew schedule
    schedule = db.query(models.CrewSchedule).filter(
        models.CrewSchedule.crew_id == assignment.crew_id,
        models.CrewSchedule.flight_number == assignment.flight_number
    ).first()
    if schedule:
        db.delete(schedule)

    db.delete(assignment)
    db.commit()
    return {"message": f"Assignment {assignment_id} and related schedule deleted."}

@router.get("/schedules")

def get_all_schedules(db: Session = Depends(get_db)):
    return db.query(models.CrewSchedule).all()

@router.post("/load-flights")
def load_flights(db: Session = Depends(get_db), flight_date: str = None):
    """Load flights with proper datetime parsing and timezone information"""
    try:
        store_luton_flights(db, flight_date)
        
        total_flights = db.query(models.Flight).count()
        
        return {
            "message": f"Flights loaded successfully with timezone information. Total flights in database: {total_flights}",
            "date": flight_date or "today"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load flights: {str(e)}")

@router.get("/debug-flights")
def debug_flights_data(db: Session = Depends(get_db), flight_date: str = None):
    """Debug endpoint to check flight data from API with timezone information"""
    try:
        from .utils import get_luton_flights, debug_flight_times
        
        flights = get_luton_flights(flight_date)
        
        for i, flight in enumerate(flights["arrivals"][:3]):
            debug_flight_times(flight, "arrival")
            
        for i, flight in enumerate(flights["departures"][:3]):
            debug_flight_times(flight, "departure")
            
        return {
            "message": "Check console output for debugging info including timezone data",
            "arrivals_count": len(flights["arrivals"]),
            "departures_count": len(flights["departures"])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Debug failed: {str(e)}")

@router.get("/flights")
def get_all_flights(db: Session = Depends(get_db)):
    flights = db.query(models.Flight).all()
    return [{
        "id": flight.id,
        "flight_number": flight.flight_number,
        "origin": flight.origin,
        "destination": flight.destination,
        "direction": flight.direction,
        "departure_time": flight.departure_time.isoformat() if flight.departure_time else None,
        "arrival_time": flight.arrival_time.isoformat() if flight.arrival_time else None,
        "duration_minutes": flight.duration_minutes,
        "duration_text": flight.duration_text,
        "timezone_info": {
            "origin_timezone": flight.origin_timezone,
            "destination_timezone": flight.destination_timezone,
            "origin_gmt_offset": flight.origin_gmt_offset,
            "destination_gmt_offset": flight.destination_gmt_offset
        }
    } for flight in flights]

@router.get("/flights/{flight_id}")
def get_flight_details(flight_id: int, db: Session = Depends(get_db)):
    """Get detailed flight information including timezone data"""
    flight = db.query(models.Flight).filter(models.Flight.id == flight_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    
    return {
        "id": flight.id,
        "flight_number": flight.flight_number,
        "origin": flight.origin,
        "destination": flight.destination,
        "direction": flight.direction,
        "departure_time": flight.departure_time.isoformat() if flight.departure_time else None,
        "arrival_time": flight.arrival_time.isoformat() if flight.arrival_time else None,
        "duration_minutes": flight.duration_minutes,
        "duration_text": flight.duration_text,
        "timezone_info": {
            "origin_timezone": flight.origin_timezone,
            "destination_timezone": flight.destination_timezone,
            "origin_gmt_offset": flight.origin_gmt_offset,
            "destination_gmt_offset": flight.destination_gmt_offset
        },
        "formatted_times": {
            "departure": f"{flight.departure_time.strftime('%Y-%m-%d %H:%M')} {flight.origin_gmt_offset or ''}" if flight.departure_time else None,
            "arrival": f"{flight.arrival_time.strftime('%Y-%m-%d %H:%M')} {flight.destination_gmt_offset or ''}" if flight.arrival_time else None
        }
    }

@router.delete("/flight/{flight_id}")
def delete_flight(flight_id: int, db: Session = Depends(get_db)):
    flight = db.query(models.Flight).filter(models.Flight.id == flight_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")

    # delete related schedules and assignments
    db.query(models.CrewSchedule).filter(models.CrewSchedule.flight_number == flight.flight_number).delete()
    db.query(models.FlightAssignment).filter(models.FlightAssignment.flight_number == flight.flight_number).delete()

    db.delete(flight)
    db.commit()
    return {"message": f"Flight {flight_id} and related schedules/assignments deleted."}

@router.get("/flights/by-date/{date}")
def get_flights_by_date(date: str, db: Session = Depends(get_db)):
    """Get all flights for a specific date with timezone information"""
    try:
        from datetime import datetime
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        flights = db.query(models.Flight).filter(
            func.date(models.Flight.departure_time) == target_date
        ).all()
        
        return [{
            "id": flight.id,
            "flight_number": flight.flight_number,
            "origin": flight.origin,
            "destination": flight.destination,
            "direction": flight.direction,
            "departure_time": flight.departure_time.isoformat() if flight.departure_time else None,
            "arrival_time": flight.arrival_time.isoformat() if flight.arrival_time else None,
            "duration_text": flight.duration_text,
            "timezone_info": {
                "origin_gmt_offset": flight.origin_gmt_offset,
                "destination_gmt_offset": flight.destination_gmt_offset
            },
            "formatted_display": f"{flight.flight_number} ({flight.origin} → {flight.destination}) - {flight.duration_text}"
        } for flight in flights]
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

# @router.get("/timezone-test")
# def test_timezone_conversion(db: Session = Depends(get_db)):
#     try:
#         from .utils import get_gmt_offset_from_timezone
#         from datetime import datetime
        
#         test_timezones = [
#             "Europe/London",
#             "America/New_York", 
#             "Asia/Tokyo",
#             "Australia/Sydney",
#             "Europe/Paris"
#         ]
        
#         results = {}
#         current_time = datetime.now()
        
#         for tz in test_timezones:
#             gmt_offset = get_gmt_offset_from_timezone(tz, current_time)
#             results[tz] = gmt_offset
            
#         return {
#             "message": "Timezone conversion test results",
#             "test_time": current_time.isoformat(),
#             "results": results
#         }
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Timezone test failed: {str(e)}")