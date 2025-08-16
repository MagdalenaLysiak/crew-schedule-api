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


COUNTRY_TIMEZONES = {
    "Poland": "Europe/Warsaw",
    "Romania": "Europe/Bucharest", 
    "United Kingdom": "Europe/London",
    "Germany": "Europe/Berlin",
    "France": "Europe/Paris",
    "Spain": "Europe/Madrid",
    "Italy": "Europe/Rome",
    "Netherlands": "Europe/Amsterdam",
    "Belgium": "Europe/Brussels",
    "Czech Republic": "Europe/Prague",
    "Hungary": "Europe/Budapest",
    "Austria": "Europe/Vienna",
    "Switzerland": "Europe/Zurich",
    "Portugal": "Europe/Lisbon",
    "Ireland": "Europe/Dublin",
    "Greece": "Europe/Athens",
    "Bulgaria": "Europe/Sofia",
    "Turkey": "Europe/Istanbul",
    "Sweden": "Europe/Stockholm",
    "Norway": "Europe/Oslo",
    "Denmark": "Europe/Copenhagen",
    "Finland": "Europe/Helsinki",
    "Croatia": "Europe/Zagreb",
    "Slovenia": "Europe/Ljubljana",
    "Slovakia": "Europe/Bratislava",
    "Serbia": "Europe/Belgrade",
    "Bosnia and Herzegovina": "Europe/Sarajevo",
    "Montenegro": "Europe/Podgorica",
    "North Macedonia": "Europe/Skopje",
    "Albania": "Europe/Tirane",
    "Lithuania": "Europe/Vilnius",
    "Latvia": "Europe/Riga",
    "Estonia": "Europe/Tallinn",
    "Luxembourg": "Europe/Luxembourg",
    "Malta": "Europe/Malta",
    "Cyprus": "Europe/Nicosia",
    "Iceland": "Atlantic/Reykjavik",
    "Moldova": "Europe/Chisinau",
    "Ukraine": "Europe/Kiev",
    "Belarus": "Europe/Minsk",
}
