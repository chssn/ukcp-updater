import datetime
import pytest
import re
from ukcp_updater.functions import Airac

airac = Airac()

def test_airac_basedate():
    assert airac.baseDate == datetime.date.fromisoformat("2019-01-02")

def test_airac_cycledays():
    assert airac.cycleDays == 28

def test_airac_today():
    assert airac.todayDate == datetime.datetime.now().date()

def test_initialise_known_date():
    result = airac.initialise("2023-06-01")
    assert result == 57

def test_initialise_not_date():
    with pytest.raises(ValueError):
        airac.initialise("2021")

def test_initialise_is_int():
    result = airac.initialise()
    assert isinstance(result, int)

def test_currentcycle_is_str():
    result = airac.currentCycle()
    assert isinstance(result, str)

def test_currentcycle_is_valid():
    assert re.match(r"20[2-9]{1}[\d]{1}\-[0-1]{1}[\d]{1}\-[0-3]{1}[\d]{1}", airac.currentCycle()) is not None

def test_currenttag_is_str():
    result = airac.currentTag()
    assert isinstance(result, str)

def test_currenttag_is_valid():
    assert re.match(r"20[2-9]{1}[\d]{1}\/[\d]{2}", airac.currentTag()) is not None