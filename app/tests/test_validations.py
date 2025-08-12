import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from fastapi import HTTPException

from app.validations import (
    validate_luton_flight_sequence,
    check_flight_time_conflict,
    flight_assignment_validation
)
from app import models
from app.config import BusinessRules


class TestLutonFlightSequence:
    def setup_method(self):
        self.db = Mock()
        self.crew_id = 1
        self.base_date = datetime(2024, 1, 15, tzinfo=timezone.utc)

    def create_mock_flight(self, flight_number, direction, origin, destination,
                           departure_time, arrival_time):
        flight = Mock(spec=models.Flight)
        flight.id = hash(flight_number) % 1000
        flight.flight_number = flight_number
        flight.direction = direction
        flight.origin = origin
        flight.destination = destination
        flight.departure_time = departure_time
        flight.arrival_time = arrival_time
        return flight

    def create_mock_assignment(self, flight):
        assignment = Mock(spec=models.FlightAssignment)
        assignment.flight = flight
        assignment.crew_id = self.crew_id
        assignment.status = "active"
        return assignment

    def test_single_luton_departure_allowed(self):
        self.db.query.return_value.join.return_value.filter.return_value.all.return_value = []

        new_flight = self.create_mock_flight(
            "EZY123", "departure", "LTN", "BCN",
            self.base_date.replace(hour=8), 
            self.base_date.replace(hour=10)
        )

        validate_luton_flight_sequence(
            self.db, self.crew_id, new_flight,
            new_flight.departure_time, new_flight.arrival_time
        )

    def test_duplicate_luton_departure_blocked(self):
        existing_flight = self.create_mock_flight(
            "EZY456", "departure", "LTN", "MAD",
            self.base_date.replace(hour=6),
            self.base_date.replace(hour=8)
        )
        existing_assignment = self.create_mock_assignment(existing_flight)

        self.db.query.return_value.join.return_value.filter.return_value.all.return_value = [existing_assignment]

        new_flight = self.create_mock_flight(
            "EZY789", "departure", "LTN", "BCN",
            self.base_date.replace(hour=10),
            self.base_date.replace(hour=12)
        )

        with pytest.raises(HTTPException) as exc_info:
            validate_luton_flight_sequence(
                self.db, self.crew_id, new_flight,
                new_flight.departure_time, new_flight.arrival_time
            )

        assert exc_info.value.status_code == 400
        assert "already has a departure flight" in exc_info.value.detail

    def test_return_flight_origin_destination_match(self):
        existing_departure = self.create_mock_flight(
            "EZY123", "departure", "LTN", "BCN",
            self.base_date.replace(hour=8),
            self.base_date.replace(hour=10)
        )
        existing_assignment = self.create_mock_assignment(existing_departure)

        self.db.query.return_value.join.return_value.filter.return_value.all.return_value = [existing_assignment]

        new_arrival = self.create_mock_flight(
            "EZY124", "arrival", "MAD", "LTN",
            self.base_date.replace(hour=14),
            self.base_date.replace(hour=16)
        )

        with pytest.raises(HTTPException) as exc_info:
            validate_luton_flight_sequence(
                self.db, self.crew_id, new_arrival,
                new_arrival.departure_time, new_arrival.arrival_time
            )

        assert exc_info.value.status_code == 400
        assert "must match the destination" in exc_info.value.detail

    def test_valid_departure_arrival_sequence(self):
        existing_departure = self.create_mock_flight(
            "EZY123", "departure", "LTN", "BCN",
            self.base_date.replace(hour=8),
            self.base_date.replace(hour=10)
        )
        existing_assignment = self.create_mock_assignment(existing_departure)

        self.db.query.return_value.join.return_value.filter.return_value.all.return_value = [existing_assignment]

        new_arrival = self.create_mock_flight(
            "EZY124", "arrival", "BCN", "LTN",
            self.base_date.replace(hour=14),
            self.base_date.replace(hour=16)
        )

        validate_luton_flight_sequence(
            self.db, self.crew_id, new_arrival,
            new_arrival.departure_time, new_arrival.arrival_time
        )


class TestFlightTimeConflicts:
    def setup_method(self):
        self.business_rules = BusinessRules()
        self.buffer_delta = timedelta(hours=self.business_rules.buffer_hours)
        self.base_date = datetime(2024, 1, 15, tzinfo=timezone.utc)

    def create_mock_assignment_with_times(self, dep_hour, arr_hour):
        flight = Mock()
        flight.flight_number = "TEST123"
        flight.departure_time = self.base_date.replace(hour=dep_hour)
        flight.arrival_time = self.base_date.replace(hour=arr_hour)

        assignment = Mock()
        assignment.flight = flight
        return assignment

    def test_no_conflict_sufficient_buffer(self):
        existing = self.create_mock_assignment_with_times(8, 10)
        new_dep = self.base_date.replace(hour=14)
        new_arr = self.base_date.replace(hour=16)

        conflict = check_flight_time_conflict(
            existing, new_dep, new_arr, self.buffer_delta
        )

        assert conflict is None

    def test_conflict_insufficient_buffer_after(self):
        existing = self.create_mock_assignment_with_times(8, 10)
        new_dep = self.base_date.replace(hour=12)
        new_arr = self.base_date.replace(hour=14)

        conflict = check_flight_time_conflict(
            existing, new_dep, new_arr, self.buffer_delta
        )

        assert conflict is not None
        assert conflict.conflict_type == "departure_too_close_after_arrival"
        assert conflict.time_gap == timedelta(hours=2)

    def test_conflict_insufficient_buffer_before(self):
        existing = self.create_mock_assignment_with_times(14, 16)
        new_dep = self.base_date.replace(hour=10)
        new_arr = self.base_date.replace(hour=12)

        conflict = check_flight_time_conflict(
            existing, new_dep, new_arr, self.buffer_delta
        )

        assert conflict is not None
        assert conflict.conflict_type == "arrival_too_close_before_departure"

    def test_conflict_flights_overlap(self):
        existing = self.create_mock_assignment_with_times(10, 14)
        new_dep = self.base_date.replace(hour=12)
        new_arr = self.base_date.replace(hour=16)

        conflict = check_flight_time_conflict(
            existing, new_dep, new_arr, self.buffer_delta
        )

        assert conflict is not None
        assert conflict.conflict_type == "flights_overlap"
        assert conflict.time_gap == timedelta(hours=2)


class TestFlightAssignmentValidation:
    def setup_method(self):
        self.db = Mock()
        self.crew_id = 1
        self.base_date = datetime(2024, 1, 15, tzinfo=timezone.utc)

        self.mock_crew = Mock()
        self.mock_crew.id = self.crew_id
        self.mock_crew.name = "Test Pilot"
        self.mock_crew.role = "pilot"

        self.mock_flight = Mock()
        self.mock_flight.id = 100
        self.mock_flight.flight_number = "EZY123"
        self.mock_flight.direction = "departure"
        self.mock_flight.origin = "LTN"
        self.mock_flight.destination = "BCN"
        self.mock_flight.departure_time = self.base_date.replace(hour=8)
        self.mock_flight.arrival_time = self.base_date.replace(hour=10)

    def test_duplicate_assignment_blocked(self):
        existing_assignment = Mock()
        existing_assignment.crew_id = self.crew_id
        existing_assignment.flight_id = self.mock_flight.id
        existing_assignment.status = "active"

        self.db.query.return_value.filter.return_value.first.return_value = existing_assignment

        with pytest.raises(HTTPException) as exc_info:
            flight_assignment_validation(
                self.db, self.crew_id, self.mock_flight,
                self.mock_flight.departure_time, self.mock_flight.arrival_time
            )

        assert exc_info.value.status_code == 400
        assert "already assigned to flight" in exc_info.value.detail

    def test_daily_flight_limit_exceeded(self):
        from unittest.mock import patch

        with patch('app.validations.validate_luton_flight_sequence'):

            self.db.query.return_value.filter.return_value.first.return_value = None

            existing_flight1 = Mock()
            existing_flight1.departure_time = self.base_date.replace(hour=6)
            existing_flight1.arrival_time = self.base_date.replace(hour=8)

            existing_flight2 = Mock()
            existing_flight2.departure_time = self.base_date.replace(hour=14)
            existing_flight2.arrival_time = self.base_date.replace(hour=16)

            assignment1 = Mock()
            assignment1.flight = existing_flight1
            assignment2 = Mock()
            assignment2.flight = existing_flight2

            self.db.query.return_value.join.return_value.filter.return_value.order_by.return_value.all.return_value = [
                assignment1, assignment2
            ]

            with pytest.raises(HTTPException) as exc_info:
                flight_assignment_validation(
                    self.db, self.crew_id, self.mock_flight,
                    self.mock_flight.departure_time, self.mock_flight.arrival_time
                )

            assert exc_info.value.status_code == 400
            assert "already has 2 flights scheduled" in exc_info.value.detail
