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


def test_tag_for_cycle_on_last_day_of_month():
    # 2027-09-30 is an AIRAC date; the old +1 day offset tagged it 2027/10
    assert airac.current_tag(input_date=datetime.date(2027, 10, 5)) == "2027/09"


def test_current_tag_defaults_to_today():
    assert isinstance(airac.current_tag(), str)
