"""
UKCP Updater
Chris Parkinson (@chssn)
"""

#!/usr/bin/env python3

# Standard Libraries
import datetime
import math

# Third Party Libraries
from loguru import logger

# Local Libraries


class Airac:
    """
    Class for general functions relating to AIRAC
    """

    def __init__(self):
        # First AIRAC date following the last cycle length modification
        self.start_date = "2019-01-02"
        self.base_date = datetime.date.fromisoformat(self.start_date)
        # Length of one AIRAC cycle
        self.cycle_days = 28

    def _initialise(self, date_in:str="") -> int:
        """Calculate the number of AIRAC cycles between any given date and the start date"""

        if date_in != "":
            input_date = datetime.date.fromisoformat(str(date_in))
        else:
            input_date = datetime.date.today()

        # How many AIRAC cycles have occured since the start date
        diff_cycles = (input_date - self.base_date) / datetime.timedelta(days=1)
        logger.debug(f"{diff_cycles} days have passed since the start date ({self.start_date})")
        # Round that number down to the nearest whole integer
        number_of_cycles = math.floor(diff_cycles / self.cycle_days)
        logger.debug(
            f"{diff_cycles} divided by {self.cycle_days} (AIRAC cycle length) and rounded down is "
            f"{number_of_cycles} AIRAC cycles")

        return number_of_cycles

    def cycle(self, next_cycle:bool=False, date_in:str="") -> datetime.date:
        """Return the date of the current AIRAC cycle"""

        number_of_cycles = self._initialise(date_in)
        if next_cycle:
            number_of_days = (number_of_cycles + 1) * self.cycle_days + 1
        else:
            number_of_days = number_of_cycles * self.cycle_days + 1
        select_cycle = self.base_date + datetime.timedelta(days=number_of_days)
        logger.success(f"The selected AIRAC cycle date is: {select_cycle}")

        return select_cycle

    def current_tag(self) -> str:
        """Returns the current tag for use with git"""
        current_cycle = self.cycle()
        # Split the current_cycle by '-' and return in format yyyy/mm
        split_cc = str(current_cycle).split("-")
        logger.debug(f"Current tag should be {split_cc[0]}/{split_cc[1]}")

        return f"{split_cc[0]}/{split_cc[1]}"
