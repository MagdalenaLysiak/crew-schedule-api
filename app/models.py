from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


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
    assignments = relationship("FlightAssignment", back_populates="flight", cascade="all, delete-orphan")


class CrewMember(Base):
    __tablename__ = "crew_members"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    role = Column(String(255), nullable=False)
    is_on_leave = Column(Boolean, default=False, nullable=False)
    assignments = relationship("FlightAssignment", back_populates="crew_member", cascade="all, delete-orphan")


class FlightAssignment(Base):
    __tablename__ = "flight_assignments"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    flight_id = Column(Integer, ForeignKey("flights.id", ondelete="CASCADE"), nullable=False)
    crew_id = Column(Integer, ForeignKey("crew_members.id", ondelete="CASCADE"), nullable=False)
    assigned_at = Column(DateTime, nullable=False)
    status = Column(String(20), default="active")
    notes = Column(String(500), nullable=True)
    flight = relationship("Flight", back_populates="assignments")
    crew_member = relationship("CrewMember", back_populates="assignments")
    __table_args__ = (
        UniqueConstraint('flight_id', 'crew_id', name='unique_flight_crew_assignment'),
    )
