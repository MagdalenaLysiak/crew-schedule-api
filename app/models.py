from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .database import Base

class Flight(Base):
    __tablename__ = "flights"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    flight_number = Column(String(20), index=True)
    origin = Column(String(255))
    destination = Column(String(255))
    direction = Column(String(10))
    duration_minutes = Column(Integer, nullable=True)
    duration_text = Column(String(20), nullable=True)
    departure_time = Column(DateTime, nullable=True)
    arrival_time = Column(DateTime, nullable=True)
    origin_timezone = Column(String(50), nullable=True)
    destination_timezone = Column(String(50), nullable=True)
    origin_gmt_offset = Column(String(10), nullable=True)
    destination_gmt_offset = Column(String(10), nullable=True)
class CrewMember(Base):
    __tablename__ = "crew_members"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    role = Column(String(255), nullable=False)
    is_on_leave = Column(Boolean, default=False, nullable=False)
    assignments = relationship(
        "FlightAssignment", 
        back_populates="crew",
        cascade="all, delete-orphan"
    )
    schedules = relationship(
        "CrewSchedule", 
        back_populates="crew",
        cascade="all, delete-orphan"
    )
class FlightAssignment(Base):
    __tablename__ = "flight_assignments"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    flight_id = Column(Integer, ForeignKey("flights.id", ondelete="CASCADE"), nullable=False)
    crew_id = Column(Integer, ForeignKey("crew_members.id", ondelete="CASCADE"), nullable=False)
    flight_number = Column(String(20), nullable=False)
    crew_name = Column(String(255))
    arrival_time = Column(DateTime, nullable=True)
    departure_time = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    crew = relationship("CrewMember", back_populates="assignments")
    flight = relationship("Flight")
class CrewSchedule(Base):
    __tablename__ = "crew_schedules"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    crew_id = Column(Integer, ForeignKey("crew_members.id", ondelete="CASCADE"), nullable=False)
    flight_id = Column(Integer, ForeignKey("flights.id", ondelete="CASCADE"), nullable=False)
    crew_name = Column(String(255), nullable=False)
    flight_number = Column(String(20), nullable=False)
    arrival_time = Column(DateTime, nullable=True)
    departure_time = Column(DateTime, nullable=True)
    origin = Column(String(255))
    destination = Column(String(255))
    duration_text = Column(String(20), nullable=True)
    crew = relationship("CrewMember", back_populates="schedules")
    flight = relationship("Flight")
