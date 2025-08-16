import pytest
import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.utils import (
    calculate_timezone_adjusted_duration,
    parse_gmt_offset
)


class TestTimezoneCalculations:
    def test_parse_gmt_offset_positive(self):
        assert parse_gmt_offset("GMT+2") == 2.0
        assert parse_gmt_offset("GMT+5:30") == 5.5
        assert parse_gmt_offset("GMT+0") == 0.0

    def test_parse_gmt_offset_negative(self):
        assert parse_gmt_offset("GMT-5") == -5.0
        assert parse_gmt_offset("GMT-8:30") == -8.5

    def test_parse_gmt_offset_invalid(self):
        assert parse_gmt_offset("invalid") == 0.0
        assert parse_gmt_offset("") == 0.0
        assert parse_gmt_offset(None) == 0.0

    def test_duration_calculation_basic(self):
        # London 10:00 GMT+0 - Barcelona 13:00 GMT+1
        # should be 2 hours (10:00 UTC - 12:00 UTC)
        dep_time = datetime(2024, 1, 15, 10, 0) 
        arr_time = datetime(2024, 1, 15, 13, 0)

        result = calculate_timezone_adjusted_duration(
            dep_time, arr_time, "GMT+0", "GMT+1"
        )

        assert result.minutes == 120
        assert result.text == "2h 0m"

    def test_duration_calculation_cross_date_new_york_to_london(self):
        # New York 23:00 GMT-5 - London 11:00 GMT+1 (next day)
        # should be 6 hours 23:00 EST (04:00 UTC) - 11:00 BST (10:00 UTC next day)
        dep_time = datetime(2024, 1, 15, 23, 0)
        arr_time = datetime(2024, 1, 16, 11, 0)

        result = calculate_timezone_adjusted_duration(
            dep_time, arr_time, "GMT-5", "GMT+1"
        )

        assert result.minutes == 360
        assert result.text == "6h 0m"

    def test_duration_calculation_cross_date_tokyo_to_london(self):
        # Tokyo 01:00 GMT+9 - London 06:00 GMT+1 (same day)
        # should be 13 hours: 01:00 JST (16:00 UTC prev day) - 06:00 BST (05:00 UTC)
        dep_time = datetime(2024, 1, 15, 1, 0)
        arr_time = datetime(2024, 1, 15, 6, 0)

        result = calculate_timezone_adjusted_duration(
            dep_time, arr_time, "GMT+9", "GMT+1"
        )

        assert result.minutes == 780
        assert result.text == "13h 0m"

    def test_duration_calculation_cross_date_london_to_sydney(self):
        # London 22:00 GMT+1 - Sydney 18:00 GMT+10 (next day)
        # should be 11 hours 22:00 BST (21:00 UTC) - 18:00 AEST (08:00 UTC next day)
        dep_time = datetime(2024, 1, 15, 22, 0)
        arr_time = datetime(2024, 1, 16, 18, 0)

        result = calculate_timezone_adjusted_duration(
            dep_time, arr_time, "GMT+1", "GMT+10"
        )

        assert result.minutes == 660
        assert result.text == "11h 0m"

    def test_duration_calculation_cross_date_dubai_to_london(self):
        # Dubai 02:00 GMT+4 - London 06:00 GMT+1 (same day)
        # should be 7 hours 02:00 GST (22:00 UTC prev day) - 06:00 BST (05:00 UTC)
        dep_time = datetime(2024, 1, 15, 2, 0)
        arr_time = datetime(2024, 1, 15, 6, 0)

        result = calculate_timezone_adjusted_duration(
            dep_time, arr_time, "GMT+4", "GMT+1"
        )

        assert result.minutes == 420
        assert result.text == "7h 0m"

    def test_duration_calculation_cross_date_london_to_singapore(self):
        # London 23:30 GMT+1 - Singapore 17:30 GMT+8 (next day)
        # should be 11 hours 23:30 BST (22:30 UTC) - 17:30 SGT (09:30 UTC next day)
        dep_time = datetime(2024, 1, 15, 23, 30)
        arr_time = datetime(2024, 1, 16, 17, 30)

        result = calculate_timezone_adjusted_duration(
            dep_time, arr_time, "GMT+1", "GMT+8"
        )

        assert result.minutes == 660
        assert result.text == "11h 0m"

    def test_invalid_duration_handling(self):
        dep_time = datetime(2024, 1, 15, 10, 0)
        arr_time = datetime(2024, 1, 15, 8, 0)

        result = calculate_timezone_adjusted_duration(
            dep_time, arr_time, "GMT+0", "GMT+0"
        )

        assert result.minutes == 0
        assert result.text == "0h 0m"

    def test_short_flight_brussels_to_luton(self):
        # Brussels 05:25 GMT+2 - Luton 04:26 GMT+1
        # should be 1h 1m
        dep_time = datetime(2024, 1, 15, 5, 25)
        arr_time = datetime(2024, 1, 15, 4, 26)

        result = calculate_timezone_adjusted_duration(
            dep_time, arr_time, "GMT+2", "GMT+1"
        )

        assert result.minutes == 61
        assert result.text == "1h 1m"

    def test_short_flight_paris_to_luton(self):
        # Paris 21:10 GMT+2 - Luton 20:25 GMT+1
        # should be 1h 15m
        dep_time = datetime(2024, 8, 14, 21, 10)
        arr_time = datetime(2024, 8, 14, 20, 25)

        result = calculate_timezone_adjusted_duration(
            dep_time, arr_time, "GMT+2", "GMT+1"
        )

        assert result.minutes == 75
        assert result.text == "1h 15m"

    def test_short_flight_luton_to_berlin(self):
        # Luton 06:00 GMT+1 - Berlin 07:30 GMT+2
        # should be 1h 30m
        dep_time = datetime(2024, 1, 15, 6, 0)
        arr_time = datetime(2024, 1, 15, 7, 30)

        result = calculate_timezone_adjusted_duration(
            dep_time, arr_time, "GMT+1", "GMT+2"
        )

        assert result.minutes == 90
        assert result.text == "1h 30m"

    def test_luton_to_romania_flight(self):
        # Luton 09:00 GMT+1 - Romania 13:45 GMT+3
        # Should be 2h 45m
        dep_time = datetime(2024, 8, 16, 9, 0)
        arr_time = datetime(2024, 8, 16, 13, 45)

        result = calculate_timezone_adjusted_duration(
            dep_time, arr_time, "GMT+1", "GMT+3"
        )

        assert result.minutes == 165
        assert result.text == "2h 45m"

    def test_luton_to_warsaw_flight(self):
        # Luton 10:00 GMT+1 - Warsaw 13:00 GMT+2
        # Should be 2h 0m
        dep_time = datetime(2024, 8, 16, 10, 0)
        arr_time = datetime(2024, 8, 16, 13, 0)

        result = calculate_timezone_adjusted_duration(
            dep_time, arr_time, "GMT+1", "GMT+2"
        )

        assert result.minutes == 120
        assert result.text == "2h 0m"

    def test_get_gmt_offset_from_country(self):
        from app.utils import get_gmt_offset_from_country

        poland_offset = get_gmt_offset_from_country("Poland")
        assert poland_offset in ["GMT+1", "GMT+2"]

        uk_offset = get_gmt_offset_from_country("United Kingdom")
        assert uk_offset in ["GMT+0", "GMT+1"]

        romania_offset = get_gmt_offset_from_country("Romania")
        assert romania_offset in ["GMT+2", "GMT+3"]

        unknown_offset = get_gmt_offset_from_country("Unknown Country")
        assert unknown_offset == "GMT+0"

    def test_get_timezone_from_iata(self):
        from app.utils import get_timezone_from_iata
        from unittest.mock import patch

        with patch('app.utils.get_airport_country') as mock_get_country:
            mock_get_country.return_value = "Poland"

            result = get_timezone_from_iata("LUZ")
            assert result in ["GMT+1", "GMT+2"]

        with patch('app.utils.get_airport_country') as mock_get_country:
            mock_get_country.return_value = ""

            result = get_timezone_from_iata("XXX")
            assert result == "GMT+0"


if __name__ == "__main__":
    pytest.main([__file__ + "::TestLutonFlightSequence::test_duplicate_luton_departure_blocked", "-v"])