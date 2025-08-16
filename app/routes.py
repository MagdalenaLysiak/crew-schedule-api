from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app import models, schemas
from .database import get_db
from .utils import store_luton_flights
from .validations import validate_flight_assignment
from .logger_service import LoggerService, get_logger_service
from .config import BusinessRules
from typing import List

router = APIRouter()
business_rules = BusinessRules()


@router.post("/crew", response_model=schemas.CrewMemberRead, status_code=201)
def create_crew(crew: schemas.CrewMemberCreate, db: Session = Depends(get_db), logger: LoggerService = Depends(get_logger_service)):
    db_crew = models.CrewMember(**crew.dict())
    db.add(db_crew)
    db.commit()
    db.refresh(db_crew)
    logger.info(f"Created crew member: {crew.name} ({crew.role})")
    return db_crew


@router.get("/crew", response_model=List[schemas.CrewMemberRead])
def get_all_crew_members(db: Session = Depends(get_db), logger: LoggerService = Depends(get_logger_service)):
    try:
        crew_members = db.query(models.CrewMember).all()
        logger.info(f"Retrieved {len(crew_members)} crew members")
        return crew_members
    except Exception as e:
        logger.error(f"Error fetching crew members: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching crew members")


@router.patch("/crew/{crew_id}", response_model=schemas.CrewMemberRead)
def update_crew(crew_id: int, crew_update: schemas.CrewMemberUpdate, db: Session = Depends(get_db), logger: LoggerService = Depends(get_logger_service)):
    crew = db.query(models.CrewMember).filter(models.CrewMember.id == crew_id).first()
    if not crew:
        raise HTTPException(status_code=404, detail="Crew member not found")

    if crew_update.role and crew_update.role.lower() != crew.role.lower():
        active_assignments = db.query(models.FlightAssignment).filter(
            models.FlightAssignment.crew_id == crew_id,
            models.FlightAssignment.status == "active"
        ).count()

        if active_assignments > 0:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot change role while crew member has {active_assignments} active flight assignments. Remove assignments first."
            )

    update_data = crew_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(crew, field, value)

    db.commit()
    db.refresh(crew)
    logger.info(f"Updated crew member {crew_id}: {update_data}")
    return crew


@router.delete("/crew/{crew_id}")
def delete_crew(crew_id: int, db: Session = Depends(get_db), logger: LoggerService = Depends(get_logger_service)):
    crew = db.query(models.CrewMember).filter(models.CrewMember.id == crew_id).first()
    if not crew:
        logger.warning(f"Crew member {crew_id} not found for deletion")
        raise HTTPException(status_code=404, detail="Crew member not found")

    db.delete(crew)
    db.commit()
    logger.info(f"Deleted crew member {crew_id} ({crew.name})")
    return {"message": f"Crew member {crew_id} and related assignments deleted."}


@router.post("/assign-flight/{crew_id}/{flight_id}", status_code=201)
def assign_flight(crew_id: int, flight_id: int, db: Session = Depends(get_db), logger: LoggerService = Depends(get_logger_service)):
    crew = db.query(models.CrewMember).filter(models.CrewMember.id == crew_id).first()
    if not crew:
        logger.warning(f"Crew member {crew_id} not found for assignment")
        raise HTTPException(status_code=404, detail="Crew member not found")

    flight = db.query(models.Flight).filter(models.Flight.id == flight_id).first()
    if not flight:
        logger.warning(f"Flight {flight_id} not found for assignment")
        raise HTTPException(status_code=404, detail="Flight not found")

    departure_time = flight.departure_time
    arrival_time = flight.arrival_time

    if not departure_time or not arrival_time:
        raise HTTPException(status_code=400, detail="Flight missing departure or arrival time")

    validate_flight_assignment(db, crew_id, flight, departure_time, arrival_time)

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
        logger.info(f"Assigned crew {crew.name} to flight {flight.flight_number}")
    except Exception as e:
        db.rollback()
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
def get_all_schedules(db: Session = Depends(get_db), logger: LoggerService = Depends(get_logger_service)):
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
        logger.error(f"Error fetching schedules: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching schedules")


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
def load_flights(db: Session = Depends(get_db), flight_date: str = None, logger: LoggerService = Depends(get_logger_service)):
    try:
        store_luton_flights(db, flight_date)
        total_flights = db.query(models.Flight).count()
        logger.info(f"Loaded flights for {flight_date or 'today'}. Total flights: {total_flights}")

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

    db.query(models.FlightAssignment).filter(models.FlightAssignment.flight_id == flight.id).delete()

    db.delete(flight)
    db.commit()
    return {"message": f"Flight {flight_id} and related schedules/assignments deleted."}


@router.delete("/flights")
def delete_all_flights(db: Session = Depends(get_db), logger: LoggerService = Depends(get_logger_service)):
    try:
        assignments_deleted = db.query(models.FlightAssignment).delete()

        flights_deleted = db.query(models.Flight).delete()

        db.commit()

        logger.info(f"Deleted {flights_deleted} flights and {assignments_deleted} assignments from database")

        return {
            "message": f"Successfully deleted {flights_deleted} flights and {assignments_deleted} assignments from database"
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting all flights: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete flights: {str(e)}")
