from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app import models, schemas
from .database import get_db
from .utils import store_luton_flights
from .validations import validate_flight_assignment
from typing import List
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

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


@router.get("/crew", response_model=List[schemas.CrewMemberRead])
def get_all_crew_members(db: Session = Depends(get_db)):
    try:
        crew_members = db.query(models.CrewMember).all()
        return crew_members
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error fetching crew members")


@router.delete("/crew/{crew_id}")
def delete_crew(crew_id: int, db: Session = Depends(get_db)):
    crew = db.query(models.CrewMember).filter(models.CrewMember.id == crew_id).first()
    if not crew:
        raise HTTPException(status_code=404, detail="Crew member not found")

    db.delete(crew)
    db.commit()
    return {"message": f"Crew member {crew_id} and related assignments deleted."}


@router.post("/assign-flight/{crew_id}/{flight_id}")
def assign_flight(crew_id: int, flight_id: int, db: Session = Depends(get_db)):
    crew = db.query(models.CrewMember).filter(models.CrewMember.id == crew_id).first()
    if not crew:
        raise HTTPException(status_code=404, detail="Crew member not found")

    flight = db.query(models.Flight).filter(models.Flight.id == flight_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")

    departure_time = flight.departure_time
    arrival_time = flight.arrival_time

    if not departure_time or not arrival_time:
        raise HTTPException(status_code=400, detail="Flight missing departure or arrival time")

    try:
        validate_flight_assignment(db, crew_id, flight, departure_time, arrival_time)
    except HTTPException as e:
        logger.error(f"Assignment validation failed: {e.detail}")
        raise e

    new_assignment = models.FlightAssignment(
        flight_id=flight.id,
        crew_id=crew.id,
        assigned_at=datetime.now(timezone.utc),
        status="active"
    )
    db.add(new_assignment)

    try:
        db.commit()
        db.refresh(new_assignment)
    except Exception as e:
        db.rollback()
        logger.error(f"Database error during assignment creation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create assignment: {str(e)}")

    return {
        "message": "Flight assigned successfully",
        "assignment_id": new_assignment.id,
        "flight_details": {
            "flight_number": flight.flight_number,
            "route": f"{flight.origin} → {flight.destination}",
            "departure": flight.departure_time.strftime('%Y-%m-%d %H:%M'),
            "arrival": flight.arrival_time.strftime('%Y-%m-%d %H:%M'),
            "duration": flight.duration_text
        },
        "crew_info": {
            "name": crew.name,
            "role": crew.role
        }
    }


@router.delete("/assignment/{assignment_id}")
def delete_assignment(assignment_id: int, db: Session = Depends(get_db)):
    assignment = db.query(models.FlightAssignment).filter(
        models.FlightAssignment.id == assignment_id
    ).first()

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    db.delete(assignment)
    db.commit()
    return {"message": f"Assignment {assignment_id} deleted successfully."}


@router.get("/schedules")
def get_all_schedules(db: Session = Depends(get_db)):
    try:
        assignments = db.query(models.FlightAssignment).join(
            models.Flight
        ).join(
            models.CrewMember
        ).filter(
            models.FlightAssignment.status == "active"
        ).all()

        schedule_items = []
        for assignment in assignments:
            flight = assignment.flight
            crew = assignment.crew_member
            schedule_item = {
                "id": assignment.id,
                "crew_id": crew.id,
                "crew_name": crew.name,
                "flight_id": flight.id,
                "flight_number": flight.flight_number,
                "departure_time": flight.departure_time.isoformat() if flight.departure_time else None,
                "arrival_time": flight.arrival_time.isoformat() if flight.arrival_time else None,
                "origin": flight.origin or "Unknown",
                "destination": flight.destination or "Unknown",
                "duration_text": flight.duration_text
            }
            schedule_items.append(schedule_item)
        return schedule_items

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching schedules: {str(e)}")


@router.get("/crew/{crew_id}/availability-check/{flight_id}")
def check_crew_availability(crew_id: int, flight_id: int, db: Session = Depends(get_db)):
    crew = db.query(models.CrewMember).filter(models.CrewMember.id == crew_id).first()
    if not crew:
        raise HTTPException(status_code=404, detail="Crew member not found")

    flight = db.query(models.Flight).filter(models.Flight.id == flight_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")

    departure_time = flight.departure_time
    arrival_time = flight.arrival_time

    if not departure_time or not arrival_time:
        raise HTTPException(status_code=400, detail="Flight missing departure or arrival time")

    try:
        validate_flight_assignment(db, crew_id, flight, departure_time, arrival_time)

        return {
            "available": True,
            "crew_name": crew.name,
            "flight_number": flight.flight_number,
            "message": f"Crew member {crew.name} is available for flight {flight.flight_number}",
            "flight_details": {
                "departure": departure_time.strftime('%Y-%m-%d %H:%M'),
                "arrival": arrival_time.strftime('%Y-%m-%d %H:%M'),
                "route": f"{flight.origin} → {flight.destination}",
                "duration": flight.duration_text
            }
        }

    except HTTPException as e:
        return {
            "available": False,
            "crew_name": crew.name,
            "flight_number": flight.flight_number,
            "reason": e.detail,
            "message": f"Crew member {crew.name} is NOT available for flight {flight.flight_number}"
        }


@router.get("/flights", response_model=List[schemas.FlightRead])
def get_all_flights(db: Session = Depends(get_db)):
    flights = db.query(models.Flight).all()
    return flights


@router.post("/load-flights")
def load_flights(db: Session = Depends(get_db), flight_date: str = None):
    try:
        store_luton_flights(db, flight_date)
        total_flights = db.query(models.Flight).count()

        return {
            "message": f"Flights loaded successfully. Total flights in database: {total_flights}",
            "date": flight_date or "today"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load flights: {str(e)}")


@router.get("/flights/{flight_id}", response_model=schemas.FlightRead)
def get_flight_details(flight_id: int, db: Session = Depends(get_db)):
    flight = db.query(models.Flight).filter(models.Flight.id == flight_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    return flight


@router.delete("/flight/{flight_id}")
def delete_flight(flight_id: int, db: Session = Depends(get_db)):
    flight = db.query(models.Flight).filter(models.Flight.id == flight_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")

    db.query(models.CrewSchedule).filter(models.CrewSchedule.flight_number == flight.flight_number).delete()
    db.query(models.FlightAssignment).filter(models.FlightAssignment.flight_number == flight.flight_number).delete()

    db.delete(flight)
    db.commit()
    return {"message": f"Flight {flight_id} and related schedules/assignments deleted."}
