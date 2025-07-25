from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .database import Base
from sqlalchemy.dialects.mysql import BIGINT as MySQLBigInt

class Flight(Base):
    __tablename__ = "flights"
    id = Column(Integer, primary_key=True, index=True)
    flight_number = Column(String(20), index=True)
    origin = Column(String(255))
    destination = Column(String(255))
    direction = Column(String(10))
    duration_minutes = Column(Integer, nullable=True)
    duration_text = Column(String(20), nullable=True)
    arrival_time = Column(DateTime, nullable=True) 
    departure_time = Column(DateTime, nullable=True) 
class CrewMember(Base):
    __tablename__ = "crew_members"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    role = Column(String(255))
    is_on_leave = Column(Boolean, default=False, nullable=False)

    assignments = relationship(
        "FlightAssignment", back_populates="crew",
        foreign_keys="FlightAssignment.crew_id"
    )
    schedules = relationship(
        "CrewSchedule", back_populates="crew",
        foreign_keys="CrewSchedule.crew_id"
    )
class FlightAssignment(Base):
    __tablename__ = "flight_assignments"
    id = Column(Integer, primary_key=True, index=True)
    flight_id = Column(MySQLBigInt(unsigned=True), ForeignKey("flights.id"))
    flight_number = Column(String(20))
    departure = Column(String(255))
    arrival = Column(String(255))
    crew_id = Column(MySQLBigInt(unsigned=True), ForeignKey("crew_members.id"))
    crew_name = Column(String(255))
    arrival_time = Column(DateTime, nullable=True) 
    departure_time = Column(DateTime, nullable=True) 

    crew = relationship(
        "CrewMember", back_populates="assignments",
        foreign_keys=[crew_id]
    )
class CrewSchedule(Base):
    __tablename__ = "crew_schedules"
    id = Column(Integer, primary_key=True, index=True)
    crew_id = Column(MySQLBigInt(unsigned=True), ForeignKey("crew_members.id"))
    crew_name = Column(String(255))
    flight_id = Column(MySQLBigInt(unsigned=True), ForeignKey("flights.id"))
    flight_number = Column(String(20))
    arrival_time = Column(DateTime, nullable=True) 
    departure_time = Column(DateTime, nullable=True) 

    crew = relationship(
        "CrewMember", back_populates="schedules",
        foreign_keys=[crew_id]
    )
