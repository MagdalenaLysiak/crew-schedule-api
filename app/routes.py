from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from app import models, schemas
from .database import get_db
from .utils import get_luton_flights, validate_flight_assignment

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

    duration_minutes = int((arrival_time - departure_time).total_seconds() / 60)
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
        crew_id=crew_id,
        crew_name=crew.name,
        duration_minutes=duration_minutes
    )
    db.add(new_assignment)

    db.commit()
    db.refresh(new_schedule)
    db.refresh(new_assignment)

    return {
        "message": "Flight assigned successfully",
        "schedule_id": new_schedule.id,
        "assignment_id": new_assignment.id,
        "duration_minutes": duration_minutes
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
def load_flights(db: Session = Depends(get_db)):
    result = get_luton_flights()
    arrivals = result["arrivals"]
    departures = result["departures"]
    added = 0

    for direction, flight_list in [("arrival", arrivals), ("departure", departures)]:
        for flight in flight_list:
            flight_number = flight.get("flight", {}).get("iata")
            origin = flight.get("departure", {}).get("airport")
            destination = flight.get("arrival", {}).get("airport")

            if not flight_number:
                continue

            existing = db.query(models.Flight).filter(
                models.Flight.flight_number == flight_number,
                models.Flight.direction == direction
            ).first()

            if existing:
                continue

            new_flight = models.Flight(
                flight_number=flight_number,
                origin=origin,
                destination=destination,
                direction=direction
            )

            db.add(new_flight)
            added += 1

    db.commit()
    return {"message": f"{added} flights added to the database."}

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
