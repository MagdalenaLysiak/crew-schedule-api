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

        duration_min, duration_text = calculate_timezone_adjusted_duration(
            dep_time, arr_time, "GMT+0", "GMT+1"
        )

        assert duration_min == 120
        assert duration_text == "2h 0m"

    def test_duration_calculation_cross_date_new_york_to_london(self):
        # New York 23:00 GMT-5 - London 11:00 GMT+1 (next day)
        # should be 6 hours 23:00 EST (04:00 UTC) - 11:00 BST (10:00 UTC next day)
        dep_time = datetime(2024, 1, 15, 23, 0)
        arr_time = datetime(2024, 1, 16, 11, 0)

        duration_min, duration_text = calculate_timezone_adjusted_duration(
            dep_time, arr_time, "GMT-5", "GMT+1"
        )

        assert duration_min == 360
        assert duration_text == "6h 0m"

    def test_duration_calculation_cross_date_tokyo_to_london(self):
        # Tokyo 01:00 GMT+9 - London 06:00 GMT+1 (same day)
        # should be 13 hours: 01:00 JST (16:00 UTC prev day) - 06:00 BST (05:00 UTC)
        dep_time = datetime(2024, 1, 15, 1, 0)
        arr_time = datetime(2024, 1, 15, 6, 0)

        duration_min, duration_text = calculate_timezone_adjusted_duration(
            dep_time, arr_time, "GMT+9", "GMT+1"
        )

        assert duration_min == 780
        assert duration_text == "13h 0m"

    def test_duration_calculation_cross_date_london_to_sydney(self):
        # London 22:00 GMT+1 - Sydney 18:00 GMT+10 (next day)
        # should be 11 hours 22:00 BST (21:00 UTC) - 18:00 AEST (08:00 UTC next day)
        dep_time = datetime(2024, 1, 15, 22, 0)
        arr_time = datetime(2024, 1, 16, 18, 0)

        duration_min, duration_text = calculate_timezone_adjusted_duration(
            dep_time, arr_time, "GMT+1", "GMT+10"
        )

        assert duration_min == 660
        assert duration_text == "11h 0m"

    def test_duration_calculation_cross_date_dubai_to_london(self):
        # Dubai 02:00 GMT+4 - London 06:00 GMT+1 (same day)
        # should be 7 hours 02:00 GST (22:00 UTC prev day) - 06:00 BST (05:00 UTC)
        dep_time = datetime(2024, 1, 15, 2, 0)
        arr_time = datetime(2024, 1, 15, 6, 0)

        duration_min, duration_text = calculate_timezone_adjusted_duration(
            dep_time, arr_time, "GMT+4", "GMT+1"
        )

        assert duration_min == 420
        assert duration_text == "7h 0m"

    def test_duration_calculation_cross_date_london_to_singapore(self):
        # London 23:30 GMT+1 - Singapore 17:30 GMT+8 (next day)
        # should be 11 hours 23:30 BST (22:30 UTC) - 17:30 SGT (09:30 UTC next day)
        dep_time = datetime(2024, 1, 15, 23, 30)
        arr_time = datetime(2024, 1, 16, 17, 30)

        duration_min, duration_text = calculate_timezone_adjusted_duration(
            dep_time, arr_time, "GMT+1", "GMT+8"
        )

        assert duration_min == 660
        assert duration_text == "11h 0m"

    def test_invalid_duration_handling(self):
        dep_time = datetime(2024, 1, 15, 10, 0)
        arr_time = datetime(2024, 1, 15, 8, 0)

        duration_min, duration_text = calculate_timezone_adjusted_duration(
            dep_time, arr_time, "GMT+0", "GMT+0"
        )

        assert duration_min == 0
        assert duration_text == "0h 0m"


if __name__ == "__main__":
    pytest.main([__file__ + "::TestLutonFlightSequence::test_duplicate_luton_departure_blocked", "-v"])