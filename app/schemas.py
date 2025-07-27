from pydantic import BaseModel, Field, computed_field, validator
from datetime import datetime
from typing import Optional, List
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
    
    @computed_field
    @property
    def route_display(self) -> str:
        if self.origin and self.destination:
            return f"{self.origin} → {self.destination}"
        return "Unknown Route"
    
    @computed_field
    @property
    def departure_display(self) -> Optional[str]:
        if self.departure_time:
            offset = f" {self.origin_gmt_offset}" if self.origin_gmt_offset else ""
            return f"{self.departure_time.strftime('%Y-%m-%d %H:%M')}{offset}"
        return None
    
    @computed_field
    @property
    def arrival_display(self) -> Optional[str]:
        if self.arrival_time:
            offset = f" {self.destination_gmt_offset}" if self.destination_gmt_offset else ""
            return f"{self.arrival_time.strftime('%Y-%m-%d %H:%M')}{offset}"
        return None

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
    
    class Config:
        from_attributes = True
class CrewMemberSimple(BaseModel):
    id: int
    name: str
    role: str
    is_on_leave: Optional[bool] = False

    class Config:
        from_attributes = True

class FlightSimple(BaseModel):
    id: int
    flight_number: str
    origin: Optional[str] = None
    destination: Optional[str] = None
    direction: Optional[str] = None
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None
    duration_text: Optional[str] = None

    class Config:
        from_attributes = True
class FlightAssignmentBase(BaseModel):
    status: Optional[str] = "active"
    notes: Optional[str] = None

class FlightAssignmentCreate(FlightAssignmentBase):
    flight_id: int
    crew_id: int

class FlightAssignmentRead(FlightAssignmentBase):
    id: int
    flight_id: int
    crew_id: int
    assigned_at: datetime
    
    flight: FlightSimple
    crew_member: CrewMemberSimple

    @computed_field
    @property
    def departure_display(self) -> str:
        if self.flight.departure_time:
            return self.flight.departure_time.strftime('%Y-%m-%d %H:%M')
        return "TBD"
    
    @computed_field
    @property
    def arrival_display(self) -> str:
        if self.flight.arrival_time:
            return self.flight.arrival_time.strftime('%Y-%m-%d %H:%M')
        return "TBD"
    
    @computed_field
    @property
    def duration_display(self) -> str:
        return self.flight.duration_text or "Unknown"

    class Config:
        from_attributes = True
class CrewMemberWithAssignments(CrewMemberBase):
    id: int
    assignments: List[FlightAssignmentRead] = []
    
    @computed_field
    @property
    def active_assignments_count(self) -> int:
        return len([a for a in self.assignments if a.status == "active"])

    class Config:
        from_attributes = True
class ScheduleItem(BaseModel):
    id: int
    crew_id: int
    crew_name: str
    flight_id: int
    flight_number: str
    departure_time: Optional[datetime]
    arrival_time: Optional[datetime]
    origin: Optional[str]
    destination: Optional[str]
    duration_text: Optional[str]
    
    @validator('crew_name', pre=True)
    def validate_crew_name(cls, v):
        if not v or str(v).isdigit():
            raise ValueError('crew_name must be a non-empty string, not a number')
        return str(v)
    
    @validator('flight_number', pre=True)
    def validate_flight_number(cls, v):
        if not v:
            raise ValueError('flight_number is required')
        v_str = str(v)
        if len(v_str) > 10 and '-' in v_str and v_str.count('-') >= 2:
            raise ValueError('flight_number appears to be corrupted (looks like a date)')
        return v_str
    
    @computed_field
    @property
    def departure_display(self) -> str:
        if self.departure_time:
            return self.departure_time.strftime('%Y-%m-%d %H:%M')
        return "TBD"
    
    @computed_field
    @property
    def arrival_display(self) -> str:
        if self.arrival_time:
            return self.arrival_time.strftime('%Y-%m-%d %H:%M')
        return "TBD"
    
    @computed_field
    @property
    def route_display(self) -> str:
        origin = self.origin or "Unknown"
        destination = self.destination or "Unknown"
        return f"{origin} → {destination}"
    
    class Config:
        from_attributes = True