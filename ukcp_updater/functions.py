"""
UKCP Updater
Chris Parkinson (@chssn)
"""

#!/usr/bin/env python3

# Standard Libraries
import os
import shutil
import filecmp

# Third Party Libraries
from loguru import logger

# Local Libraries

# https://vatsim.dev/resources/ratings
RATING_DICT = {
    "Observer": 1,
    "Tower Trainee (S1)": 2,
    "Tower Controller (S2)": 3,
    "TMA Controller (S3)": 4,
    "Enroute Controller (C1)": 5,
    "Senior Controller (C2)": 6,
    "Senior Controller (C3)": 7,
    "Instuctor (I1)": 8,
    "Senior Instuctor (I2)": 9,
    "Senior Instuctor (I3)": 10,
    "Supervisor": 11,
    "Administrator": 12
}

FACILITY_TYPES = {
    "Observer": 0,
    "Flight Service Station": 1,
    "Clearance Delivery": 2,
    "Ground": 3,
    "Tower": 4,
    "Approach/Departure": 5,
    "Enroute": 6,
}

IGNORE_EXT:set = set()
IGNORE_NAMES = {"vStripsESP.dll"}

def should_ignore(filename: str) -> bool:
    """should it be ignored"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in IGNORE_EXT or filename in IGNORE_NAMES

def sync_cache_to_live(cache_dir: str, live_dir: str):
    """
    Copy cache -> live
    Preserve extra files in live
    Overwrite outdated files
    """

    for root, dirs, files in os.walk(cache_dir):

        rel = os.path.relpath(root, cache_dir)
        live_root = os.path.join(live_dir, rel)

        # Ensure directory exists
        os.makedirs(live_root, exist_ok=True)

        # Copy/update files
        for name in files:
            logger.debug(f"Sync {name}")
            if should_ignore(name):
                continue
            src = os.path.join(root, name)
            dst = os.path.join(live_root, name)

            # If file missing → copy
            if not os.path.exists(dst):
                shutil.copy2(src, dst)
                continue

            # If exists but differs → overwrite
            if not filecmp.cmp(src, dst, shallow=False):
                shutil.copy2(src, dst)

        # Ensure subdirs exist
        for name in dirs:
            os.makedirs(os.path.join(live_root, name), exist_ok=True)
