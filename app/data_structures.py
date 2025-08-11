from dataclasses import dataclass


@dataclass
class DurationResult:
    minutes: int
    text: str
    is_valid: bool = True
