from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from .database import get_db
from .utils import get_luton_flights
from .models import CrewSchedule
from datetime import datetime, timedelta, date

router = APIRouter()

@router.post("/crew", response_model=schemas.CrewMemberRead)
def create_crew(crew: schemas.CrewMemberCreate, db: Session = Depends(get_db)):
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

    departure_time = datetime(2025, 7, 25, 14, 0)
    arrival_time = datetime(2025, 7, 25, 16, 0)

    #block scheduling conflict
    existing_schedule = db.query(models.CrewSchedule).filter(
        models.CrewSchedule.crew_id == crew_id
    ).all()

    for schedule in existing_schedule:
        if schedule.departure_time.date() == departure_time.date():
            raise HTTPException(
                status_code=400,
                detail=f"Crew member already has a flight on {departure_time.date()}",
            )

    new_schedule = models.CrewSchedule(
        crew_id=crew_id,
        crew_name=crew.name,
        flight_number=flight.flight_number,
        departure_time=departure_time,
        arrival_time=arrival_time,
    )
    db.add(new_schedule)

    new_assignment = models.FlightAssignment(
        flight_number=flight.flight_number,
        departure=departure_time.strftime("%Y-%m-%d %H:%M"),
        arrival=arrival_time.strftime("%Y-%m-%d %H:%M"),
        crew_id=crew_id,
        crew_name=crew.name,
    )
    db.add(new_assignment)

    db.commit()
    db.refresh(new_schedule)
    db.refresh(new_assignment)

    return {
        "message": "Flight assigned successfully",
        "schedule_id": new_schedule.id,
        "assignment_id": new_assignment.id,
    }

@router.get("/schedules")

def get_all_schedules(db: Session = Depends(get_db)):
    schedules = db.query(models.CrewSchedule).all()
    return schedules

@router.post("/load-flights")
def load_flights(db: Session = Depends(get_db)):
    flights = get_luton_flights()
    added = 0

    for flight in flights:
        flight_number = flight.get("flight", {}).get("iata")
        origin = flight.get("departure", {}).get("airport")
        destination = flight.get("arrival", {}).get("airport")

        if not flight_number:
            continue

        existing = db.query(models.Flight).filter(
            models.Flight.flight_number == flight_number
        ).first()

        if existing:
            continue

        new_flight = models.Flight(
            flight_number=flight_number,
            origin=origin,
            destination=destination,
        )

        db.add(new_flight)
        added += 1

    db.commit()
    return {"message": f"{added} flights added to the database."}
