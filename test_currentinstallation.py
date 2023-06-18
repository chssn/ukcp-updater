import os
import pytest
import random
import re
import string
import git
from unittest.mock import patch
from ukcp_updater.functions import CurrentInstallation

letters = string.ascii_letters + string.digits + string.punctuation
rnd_string = ''.join(random.choice(letters) for _ in range(64))
current_installation = CurrentInstallation()

@pytest.fixture
def mock_current():
    rtn = CurrentInstallation()
    return rtn

def test_location(mock_current, mocker):
    mocker.patch('os.path.join', return_value=rnd_string)
    mocker.patch('os.path.exists', return_value=True)

    result = mock_current.location()
    assert result == rnd_string