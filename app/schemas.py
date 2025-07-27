from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, List

class FlightAssignmentBase(BaseModel):
    flight_number: str
    crew_name: Optional[str] = None
    duration_minutes: Optional[int] = None

class FlightAssignmentCreate(FlightAssignmentBase):
    flight_id: int
    crew_id: int
    departure_time: datetime
    arrival_time: datetime

class FlightAssignmentRead(FlightAssignmentBase):
    id: int
    flight_id: int
    crew_id: int
    departure_time: datetime
    arrival_time: datetime
    departure: str = Field(alias="departure_time")
    arrival: str = Field(alias="arrival_time")
    
    @validator('departure', pre=True, always=True)
    def format_departure(cls, v, values):
        if 'departure_time' in values:
            dt = values['departure_time']
            if isinstance(dt, datetime):
                return dt.strftime('%Y-%m-%d %H:%M')
        return v
    
    @validator('arrival', pre=True, always=True) 
    def format_arrival(cls, v, values):
        if 'arrival_time' in values:
            dt = values['arrival_time']
            if isinstance(dt, datetime):
                return dt.strftime('%Y-%m-%d %H:%M')
        return v

    class Config:
        from_attributes = True
        allow_population_by_field_name = True

class CrewScheduleBase(BaseModel):
    crew_name: str
    flight_number: str
    origin: Optional[str] = None
    destination: Optional[str] = None
    duration_text: Optional[str] = None

class CrewScheduleCreate(CrewScheduleBase):
    crew_id: int
    flight_id: int
    departure_time: datetime
    arrival_time: datetime

class CrewScheduleRead(CrewScheduleBase):
    id: int
    crew_id: int
    flight_id: int
    departure_time: datetime
    arrival_time: datetime

    class Config:
        from_attributes = True

class CrewMemberBase(BaseModel):
    name: str
    role: str
    is_on_leave: Optional[bool] = False

class CrewMemberCreate(CrewMemberBase):
    pass

class CrewMemberRead(CrewMemberBase):
    id: int
    assignments: List[FlightAssignmentRead] = []
    schedules: List[CrewScheduleRead] = []

    class Config:
        from_attributes = True

class FlightBase(BaseModel):
    flight_number: str
    origin: Optional[str] = None
    destination: Optional[str] = None
    direction: Optional[str] = None
    duration_minutes: Optional[int] = None
    duration_text: Optional[str] = None
    origin_timezone: Optional[str] = None
    destination_timezone: Optional[str] = None
    origin_gmt_offset: Optional[str] = None
    destination_gmt_offset: Optional[str] = None

class FlightCreate(FlightBase):
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None

class FlightRead(FlightBase):
    id: int
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None

    class Config:
        from_attributes = True

class FlightAssignmentSimple(BaseModel):
    id: int
    flight_id: int
    crew_id: int
    flight_number: str
    crew_name: Optional[str] = None
    departure: str
    arrival: str
    duration_minutes: Optional[int] = None
    
    @classmethod
    def from_orm_obj(cls, obj):
        return cls(
            id=obj.id,
            flight_id=obj.flight_id,
            crew_id=obj.crew_id,
            flight_number=obj.flight_number,
            crew_name=obj.crew_name,
            departure=obj.departure_time.strftime('%Y-%m-%d %H:%M') if obj.departure_time else '',
            arrival=obj.arrival_time.strftime('%Y-%m-%d %H:%M') if obj.arrival_time else '',
            duration_minutes=obj.duration_minutes
        )

class CrewMemberSimple(BaseModel):
    id: int
    name: str
    role: str
    is_on_leave: bool = False
    assignments: List[FlightAssignmentSimple] = []

    @classmethod
    def from_orm_obj(cls, obj):
        return cls(
            id=obj.id,
            name=obj.name,
            role=obj.role,
            is_on_leave=obj.is_on_leave,
            assignments=[FlightAssignmentSimple.from_orm_obj(a) for a in obj.assignments]
        )