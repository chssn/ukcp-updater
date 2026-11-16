import datetime

import pytest

from ukcp_updater.airac import Airac

airac = Airac()


def test_airac_cycledays():
    assert airac.cycle_days == 28


def test_base_date_is_its_own_cycle():
    assert airac.cycle(input_date=airac.base_date) == airac.base_date


@pytest.mark.parametrize("today, expected", [
    ("2026-01-22", "2026-01-22"),
    ("2026-02-18", "2026-01-22"),
    ("2026-02-19", "2026-02-19"),
    ("2026-10-28", "2026-10-01"),
    ("2026-10-29", "2026-10-29"),
])
def test_cycle_known_dates(today, expected):
    result = airac.cycle(input_date=datetime.date.fromisoformat(today))
    assert result == datetime.date.fromisoformat(expected)


def test_next_cycle():
    result = airac.cycle(next_cycle=True, input_date=datetime.date(2026, 1, 22))
    assert result == datetime.date(2026, 2, 19)


@pytest.mark.parametrize("today, expected", [
    # Tags are yyyy/<cycle number>, not yyyy/<month>
    ("2026-01-22", "2026/01"),
    ("2026-10-28", "2026/10"),  # cycle 2610 effective 2026-10-01
    ("2026-11-16", "2026/11"),  # cycle 2611 effective 2026-10-29
    ("2026-12-24", "2026/13"),  # 13th cycle of the year
    ("2027-01-21", "2027/01"),
    ("2027-10-05", "2027/10"),  # cycle 2710 effective 2027-09-30
])
def test_current_tag_uses_cycle_number(today, expected):
    assert airac.current_tag(input_date=datetime.date.fromisoformat(today)) == expected


def test_current_tag_defaults_to_today():
    assert isinstance(airac.current_tag(), str)
