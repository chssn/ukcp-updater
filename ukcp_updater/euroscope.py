"""
UKCP Updater
Chris Parkinson (@chssn)
"""

#!/usr/bin/env python3

# Standard Libraries
import ctypes
import os
from tkinter import Tk
from tkinter import filedialog
from packaging.version import Version

# Third Party Libraries
from loguru import logger

# Local Libraries


class Euroscope:
    """
    Check the version of EuroScope currently installed
    """

    def __init__(self) -> None:
        # This version number is defined in the EuroScope.exe properties
        self.minimum_version = "3.2.2.0"

    @staticmethod
    def installed_location() -> str:
        """Finds out where EuroScope has been installed"""

        # This is the default install location for EuroScope
        default_path = r"C:\Program Files (x86)\EuroScope\EuroScope.exe"
        logger.debug(f"Testing to see if {default_path} is valid...")

        if os.path.exists(default_path):
            logger.success("EuroScope is installed in the default location")
            return default_path
        else:
            # This first bit just hides the tkinter box so only file explorer is displayed
            root = Tk()
            root.withdraw()
            logger.warning("EuroScope doesn't appear to be installed in the default directory")
            install_path = filedialog.askopenfilename(title='Select EuroScope exe file')
            logger.info(f"User provided {install_path} for EuroScope.exe location")
            return install_path

    def version(self) -> str:
        """Find out the EuroScope version"""

        exe_path = self.installed_location()

        # Load the version.dll library
        version_dll = ctypes.WinDLL('version.dll')

        # Get the size of the file version info
        size = version_dll.GetFileVersionInfoSizeW(exe_path, None)

        # Create a buffer to hold the file version info
        buffer = ctypes.create_string_buffer(size)

        # Retrieve the file version info
        version_dll.GetFileVersionInfoW(exe_path, None, size, buffer)

        # Query the file description
        description = ctypes.c_wchar_p()
        description_length = ctypes.c_uint()

        version_dll.VerQueryValueW(
            buffer,
            r'\StringFileInfo\040904b0\FileVersion',
            ctypes.byref(description),
            ctypes.byref(description_length))

        # Print the description
        version_number = description.value
        logger.debug(f"EuroScope version {version_number} has been found")
        return str(version_number)

    def compare(self) -> bool:
        """Compare the found version against the minimum required version"""

        installed_version = self.version()
        minimum_version = self.minimum_version

        # Carry out the comparison
        if Version(installed_version) > Version(minimum_version):
            logger.success(f"Installed version of EuroScope (v{installed_version}) "
                           "is compatible with this script")
            return True
        raise ValueError(f"EuroScope version (v{installed_version}) is incompatible with this "
                         "application. Download the latest version from "
                         "https://www.euroscope.hu/wp/installation/")
