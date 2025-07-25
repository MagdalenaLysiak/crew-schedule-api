from pydantic import BaseModel
from typing import List, Optional

class CrewMemberBase(BaseModel):
    name: str
    role: str

class CrewMemberCreate(CrewMemberBase):
    pass

class FlightAssignmentRead(BaseModel):
    id: int
    flight_number: str
    departure: str
    arrival: str

    class Config:
        orm_mode = True

class CrewMemberRead(CrewMemberBase):
    id: int
    assignments: List[FlightAssignmentRead] = []

    class Config:
        orm_mode = True
