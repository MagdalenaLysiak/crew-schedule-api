from dataclasses import dataclass
from typing import List


@dataclass
class BusinessRules:
    buffer_hours: int = 3
    max_flights_per_day: int = 2
    max_pilots_per_flight: int = 2
    max_attendants_per_flight: int = 4
    duty_time_limit_hours: int = 14
    valid_crew_roles: List[str] = None

    def __post_init__(self):
        if self.valid_crew_roles is None:
            self.valid_crew_roles = ["pilot", "flight attendant"]


@dataclass
class ApiConfig:
    base_url: str = "http://api.aviationstack.com/v1/flights"
    airport_code: str = "LTN"
    max_flight_duration_hours: int = 20
