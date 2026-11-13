"""Unit tests for presentation formatters (utils/formatters.py)."""

from datetime import datetime, time
import pytest

from utils.formatters import (
    format_time_12h,
    format_time_range_12h,
    generate_12h_time_options,
    parse_time_12h_to_24h,
    parse_time_to_time_obj,
)


class TestFormatTime12h:
    """Test format_time_12h conversion behavior."""

    def test_morning_and_evening_strings(self):
        assert format_time_12h("06:00") == "6:00 AM"
        assert format_time_12h("08:30") == "8:30 AM"
        assert format_time_12h("18:00") == "6:00 PM"
        assert format_time_12h("21:45") == "9:45 PM"

    def test_midnight_and_noon(self):
        assert format_time_12h("00:00") == "12:00 AM"
        assert format_time_12h("12:00") == "12:00 PM"
        assert format_time_12h("12:30") == "12:30 PM"
        assert format_time_12h("00:15") == "12:15 AM"

    def test_seconds_included(self):
        assert format_time_12h("19:45:00") == "7:45 PM"
        assert format_time_12h("07:15:30") == "7:15 AM"

    def test_datetime_time_and_datetime_objects(self):
        assert format_time_12h(time(14, 30)) == "2:30 PM"
        assert format_time_12h(time(0, 0)) == "12:00 AM"
        assert format_time_12h(time(12, 0)) == "12:00 PM"
        dt = datetime(2026, 11, 13, 19, 20)
        assert format_time_12h(dt) == "7:20 PM"

    def test_already_formatted_am_pm(self):
        assert format_time_12h("6:00 PM") == "6:00 PM"
        assert format_time_12h("10:30 AM") == "10:30 AM"

    def test_none_empty_and_invalid_fallback(self):
        assert format_time_12h(None) == "—"
        assert format_time_12h("") == "—"
        assert format_time_12h("null") == "—"
        assert format_time_12h("None") == "—"
        assert format_time_12h(None, fallback="Not set") == "Not set"
        assert format_time_12h("invalid_time") == "invalid_time"


class TestFormatTimeRange12h:
    """Test format_time_range_12h conversion behavior."""

    def test_valid_ranges(self):
        assert format_time_range_12h("07:00", "08:30") == "7:00 AM – 8:30 AM"
        assert format_time_range_12h("18:00", "21:00", separator=" to ") == "6:00 PM to 9:00 PM"
        assert format_time_range_12h(time(9, 0), time(10, 15)) == "9:00 AM – 10:15 AM"

    def test_missing_and_empty_endpoints(self):
        assert format_time_range_12h(None, None) == "—"
        assert format_time_range_12h("", "") == "—"
        assert format_time_range_12h("09:00", None) == "9:00 AM – —"


class TestParseTime12hTo24h:
    """Test parse_time_12h_to_24h canonical conversion."""

    def test_standard_am_pm_parsing(self):
        assert parse_time_12h_to_24h("6:00 PM") == "18:00"
        assert parse_time_12h_to_24h("06:00 PM") == "18:00"
        assert parse_time_12h_to_24h("7:30 AM") == "07:30"
        assert parse_time_12h_to_24h("07:30 AM") == "07:30"
        assert parse_time_12h_to_24h("12:00 AM") == "00:00"
        assert parse_time_12h_to_24h("12:00 PM") == "12:00"
        assert parse_time_12h_to_24h("11:59 PM") == "23:59"

    def test_already_24h_pass_through(self):
        assert parse_time_12h_to_24h("18:00") == "18:00"
        assert parse_time_12h_to_24h("07:30") == "07:30"
        assert parse_time_12h_to_24h("00:00") == "00:00"

    def test_object_inputs(self):
        assert parse_time_12h_to_24h(time(18, 45)) == "18:45"
        dt = datetime(2026, 11, 13, 8, 15)
        assert parse_time_12h_to_24h(dt) == "08:15"

    def test_invalid_and_empty_inputs(self):
        assert parse_time_12h_to_24h(None) is None
        assert parse_time_12h_to_24h("") is None
        assert parse_time_12h_to_24h("invalid") is None


class TestTimeOptionsAndObjectParser:
    """Test generate_12h_time_options and parse_time_to_time_obj."""

    def test_generate_12h_options_15m_count_and_boundaries(self):
        options = generate_12h_time_options(step_minutes=15)
        assert len(options) == 96
        assert options[0] == "12:00 AM"
        assert options[1] == "12:15 AM"
        assert options[48] == "12:00 PM"
        assert options[-1] == "11:45 PM"

    def test_roundtrip_all_options(self):
        options = generate_12h_time_options(step_minutes=30)
        assert len(options) == 48
        for opt in options:
            h24 = parse_time_12h_to_24h(opt)
            assert h24 is not None
            back_12h = format_time_12h(h24)
            assert back_12h == opt

    def test_parse_time_to_time_obj(self):
        t1 = parse_time_to_time_obj("6:00 PM")
        assert t1 == time(18, 0)
        t2 = parse_time_to_time_obj("07:30")
        assert t2 == time(7, 30)
        t_fallback = parse_time_to_time_obj("invalid", fallback=time(12, 0))
        assert t_fallback == time(12, 0)
