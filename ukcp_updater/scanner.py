"""
UKCP Updater
Chris Parkinson (@chssn)
"""

#!/usr/bin/env python3

# Standard Libraries
import csv
import os
import re
from tkinter import Tk
from tkinter import filedialog
from typing import List

# Third Party Libraries
import py7zr
import requests # type: ignore
from InquirerPy.inquirer import text, confirm, number, secret, select # type: ignore
from InquirerPy.base.control import Choice # type: ignore
from InquirerPy.validator import EmptyInputValidator # type: ignore
from loguru import logger

# Local Libraries
from ukcp_updater import airac, functions


class CurrentInstallation:
    """
    Actions to be carried on the current installation of UKCP
    """

    def __init__(self, live:str="ukcp-live") -> None:
        self.ukcp_location = self._location(live)

        # Get the current AIRAC
        airac_init = airac.Airac()
        self.airac = airac_init.current_tag()

        # Sector file base URL
        self.sector_url = "http://docs.vatsim.uk/General/Software%20Downloads/Files/"

        # Test that the sector file exists before wrecking everything!
        self._check_if_sector_file_dl_exists()

        # Set some vars to do with specific plugins
        self.plugin_vfpc = False
        self.plugin_cdm = False

    def _check_if_sector_file_dl_exists(self) -> bool:
        """Tests to see if the sector file download exists"""
        airac_format = str(self.airac.replace("/", "_"))
        url = f"{self.sector_url}UK_{airac_format}.7z"
        logger.debug(f"Sector file url {url}")
        sector_7z = requests.get(url, timeout=30)
        if sector_7z.status_code == 200:
            return True
        raise FileExistsError("Unable to locate")

    def _location(self, live:str) -> str:
        """Find the current location of UKCP"""

        # This is the default install location for EuroScope
        appdata_folder = os.environ["APPDATA"]
        default_path = os.path.join(appdata_folder, 'EuroScope', live, 'UK')
        logger.debug(f"Testing to see if {default_path} is valid...")

        if os.path.exists(default_path):
            logger.debug(
                f"UK Controller Pack data is installed in the default location {default_path}")
            return default_path
        else:
            # This first bit just hides the tkinter box so only file explorer is displayed
            root = Tk()
            root.withdraw()
            logger.warning("UK Controller Pack data is not installed in the default location")
            install_path = filedialog.askopenfilename(title='Select UK Controller Pack Folder')
            logger.info(f"User provided {install_path} for UK Controller Pack location")
            return install_path

    @staticmethod
    def manual_entry(
        return_user_data:dict,
        realname:bool=False,
        certificate:bool=False,
        password:bool=False,
        rating:bool=False,
        all_data:bool=True) -> dict:
        """Allow manual entry of user data"""

        if realname or all_data:
            return_user_data["realname"] = text(
                message="Enter your real name or CID:",
                validate=EmptyInputValidator()).execute()

        if certificate or all_data:
            return_user_data["certificate"] = number(
                message="Enter your certificate or CID:",
                min_allowed=800000,
                validate=EmptyInputValidator()).execute()

        if password or all_data:
            return_user_data["password"] = secret(
                message="Enter your password:",
                validate=EmptyInputValidator()
            ).execute()

        if rating or all_data:
            choices:List[Choice] = []
            for i, j in functions.RATING_DICT.items():
                choices.append(Choice(j, name=i))
            return_user_data["rating"] = select(
                message="Select your rating:",
                choices=choices,
                default=None,
                ).execute()

        return return_user_data

    def user_settings(self) -> dict:
        """Parse current *.prf files for custom settings"""

        plugin_out:List[str] = []
        return_user_data:dict = {}
        # Init the return_user_data keys
        return_user_data.update({
            "realname": None,
            "certificate": None,
            "password": None,
            "facility": None,
            "rating": None,
            "plugins": None,
            "vccs_ptt_g2a": None,
            "vccs_ptt_g2g": None,
            "vccs_capture_mode": None,
            "vccs_capture_device": None,
            "vccs_playback_mode": None,
            "vccs_playback_device": None,
            "hoppies_cpdlc_password": None,
        })

        def menu_option(title:str, data_type:str, options:list) -> str:
            """Menu to select one option out of many!"""
            choices:list = []
            if data_type == "rating":
                for i, j in functions.RATING_DICT.items():
                    choices.append(Choice(j, name=i))
            elif data_type == "facility":
                for i, j in functions.FACILITY_TYPES.items():
                    choices.append(Choice(j, name=i))
            else:
                choices = options

            response = select(
                message=title,
                choices=choices,
            ).execute()

            return response

        # Ask the user if they consent to file search for custom settings
        msg = "Do you want us to search your existing files for any custom settings?"
        proceed = confirm(message=msg, default=True).execute()
        if not proceed:
            logger.warning("User consent not given for file search")
            return_user_data = self.manual_entry(return_user_data, all_data=True)
        else:
            logger.success("User consent given for file search")

            # List all the regex patterns
            patterns = {
                "realname": r"LastSession\trealname\t(.*)",
                "certificate": r"LastSession\tcertificate\t([0-9]{4,})",
                "password": r"LastSession\tpassword\t(.*)",
                "facility": r"LastSession\tfacility\t([0-9]{1})",
                "rating": r"LastSession\trating\t([0-9]{1})",
                "plugins": r"Plugins\tPlugin[0-9]{1,2}\t([A-Z]{1}\:\\.*)",
                "vccs_ptt_g2a": r"TeamSpeakVccs\tTs3G2APtt\t([0-9]{1,10})",
                "vccs_ptt_g2g": r"TeamSpeakVccs\tTs3G2GPtt\t([0-9]{1,10})",
                "vccs_playback_mode": r"TeamSpeakVccs\tPlaybackMode\t(.*)",
                "vccs_playback_device": r"TeamSpeakVccs\tPlaybackDevice\t(.*)",
                "vccs_capture_mode": r"TeamSpeakVccs\tCaptureMode\t(.*)",
                "vccs_capture_device": r"TeamSpeakVccs\tCaptureDevice\t(.*)",
                "hoppies_cpdlc_password": r"vSMR\:cpdlc\_password\:(.*)",
            }

            # Init the return_user_data keys
            return_user_data.update({
                "realname": set(),
                "certificate": set(),
                "password": set(),
                "facility": set(),
                "rating": set(),
                "plugins": set(),
                "vccs_ptt_g2a": set(),
                "vccs_ptt_g2g": set(),
                "vccs_capture_mode": set(),
                "vccs_capture_device": set(),
                "vccs_playback_mode": set(),
                "vccs_playback_device": set(),
                "hoppies_cpdlc_password": set(),
            })

            # Iterate over files in the directory and search within each file
            for root, dirs, files in os.walk(self.ukcp_location):
                for file_name in files:
                    if file_name.endswith(".prf"):
                        file_path = os.path.join(root, file_name)
                        logger.debug(f"Found {file_path}")
                        with open(file_path, "r", encoding="utf-8") as file:
                            for line in file:
                                for key, pattern in patterns.items():
                                    match = re.match(pattern, line)
                                    if match:
                                        return_user_data[key].add(match.group(1))

            # Process the collected data
            for key, values in return_user_data.items():
                if key != "password" and key != "plugins":
                    if len(values) > 1:
                        logger.warning(f"More than one setting for {key} has been found!")
                        menu_select = menu_option(
                            f"Select the {key} you wish to use below:", key, list(values))
                        return_user_data[key] = menu_select
                    else:
                        return_user_data[key] = next(iter(values), None)
                elif key == "password":
                    # Passwords handled separately
                    if len(values) > 1:
                        logger.warning("More than one setting for your password has been found!")
                        logger.info(
                            f"We found {len(values)} different passwords "
                            "however won't display them!")
                        logger.info("Please enter your password below. Note that no "
                                    "characters or *'s will be displayed!")
                        return_user_data["password"] = secret(
                            message="Enter your password:",
                            validate=EmptyInputValidator()
                        ).execute()
                    elif len(values) == 1:
                        return_user_data["password"] = list(values)[0]
                elif key == "plugins":
                    # Handle plugins separately
                    plugins = return_user_data["plugins"]
                    if plugins:
                        logger.info("The following custom (non UKCP) plugins have been detected:")
                        plugin_out = []

                        # Loop over the plugins and ask for confirmation for each one
                        for plugin in list(plugins):
                            print(plugin)
                            response = input("Do you want to add this plugin? [Y|n] ")
                            if response.upper() == "N":
                                continue
                            else:
                                plugin_out.append(str(plugin))
                                # If the VFPC plugin is going to be used then
                                # set the environmental variable
                                if re.match(r".*VFPC\.dll", plugin):
                                    logger.debug("VFPC.dll specific functions enabled")
                                    self.plugin_vfpc = True
                                # If the CDM plugin is going to be used then
                                # set the environmental variable
                                if re.match(r".*CDM\.dll", plugin):
                                    logger.debug("CDM.dll specific functions enabled")
                                    self.plugin_cdm = True
                    else:
                        logger.info("No custom (non UKCP) plugins were detected")
                        plugin_out = ["No custom (non UKCP) plugins were detected"]

                    return_user_data["plugins"] = plugin_out

        # Check for "None" entries
        if return_user_data["realname"] is None:
            return_user_data = self.manual_entry(return_user_data, realname=True)
        if return_user_data["certificate"] is None:
            return_user_data = self.manual_entry(return_user_data, certificate=True)
        if return_user_data["password"] is None:
            return_user_data = self.manual_entry(return_user_data, password=True)
        if return_user_data["rating"] is None:
            return_user_data = self.manual_entry(return_user_data, rating=True)

        # User information
        print("The following data will be appended to all profiles in the UK Controller Pack")
        print("This is a LOCAL operation and none of your data is transmitted "
              "away from your computer!")
        print(f"Real Name:\t\t{return_user_data['realname']}")
        print(f"Certificate:\t\t{return_user_data['certificate']}")
        print("Password:\t\t[NOT DISPLAYED]")
        print(f"Rating:\t\t\t{return_user_data['rating']}")
        for j, i in enumerate(plugin_out):
            if j == 0:
                print(f"Plugins:\t\t{i}")
            else:
                print(f"\t\t\t{i}")
        print(f"VCCS Nickname:\t\t{return_user_data['certificate']}\t\tnote: this has just been "
              "copied from your certificate")
        print(f"VCCS G2A PTT:\t\t{return_user_data['vccs_ptt_g2a']}\t\tnote: this is a "
              "scancode representation of a phyiscal key")
        print(f"VCCS G2G PTT:\t\t{return_user_data['vccs_ptt_g2g']}\t\tnote: this is a "
              "scancode representation of a phyiscal key")
        print(f"VCCS Capture Mode:\t{return_user_data['vccs_capture_mode']}")
        print(f"VCCS Playback Mode:\t{return_user_data['vccs_playback_mode']}")
        print(f"VCCS Capture Mode:\t{return_user_data['vccs_capture_device']}")
        print(f"VCCS Playback Mode:\t{return_user_data['vccs_playback_device']}")
        print("Hoppies CPDLC Password:\t[NOT DISPLAYED]")
        input("Press ENTER to continue...")

        return return_user_data

    def apply_settings(self, settings_prf:dict, settings_asr:dict):
        """Applies settings to relevant files"""

        def iter_files(ext:str, file_mode:str):
            """Iterate over files in the directory and search within each file"""
            def decorator_func(func):
                def wrapper(*args, **kwargs):
                    for root, dirs, files in os.walk(self.ukcp_location):
                        for file_name in files:
                            if file_name.endswith(ext):
                                file_path = os.path.join(root, file_name)
                                logger.debug(f"Found {file_path}")
                                with open(file_path, file_mode) as file:
                                    lines = file.readlines()
                                    file.seek(0)
                                    func(lines, file, file_path, *args, **kwargs)
                return wrapper
            return decorator_func

        def get_sector_file():
            """Get the sector file name"""

            loop = True
            sector_file_list = [
                'Akrotiri LCRA.sct',
                'Ascension and St Helena.sct',
                'Falkland.sct',
                'Gibraltar LXGB.sct'
                ]
            while loop:
                sector_file = []
                sector_fn = []
                for root, dirs, files in os.walk(self.ukcp_location):
                    for file_name in files:
                        if file_name.endswith(".sct"):
                            sector_file.append(os.path.join(root, file_name))
                            sector_fn.append(file_name)

                if len(sector_file) == 0:
                    sector_file.append("*")
                    sector_fn.append("*")
                for sf in sector_file:
                    if re.match(r"^.*\\UK_20\d{2}_\d{2}\.sct$", sf):
                        logger.info(f"Sector file found at {sf}")

                        # Check the sector file matches the current AIRAC cycle
                        airac_format = str(self.airac.replace("/", "_"))
                        if airac_format not in sf:
                            logger.warning("Your sector file appears out of date with the "
                                        f"current {self.airac} release!")
                            msg = "Would you like to download the latest sector file?"
                            proceed = confirm(message=msg, default=True).execute()
                            if proceed:
                                # Download the latest file
                                url = f"{self.sector_url}UK_{airac_format}.7z"
                                logger.debug(f"Sector file url {url}")
                                sector_7z = requests.get(url, timeout=30)

                                # Write it to local file
                                file_path = f"local\\UK_{airac_format}.7z"
                                with open(file_path, "wb") as file:
                                    file.write(sector_7z.content)

                                # Extract the contents of the archive
                                with py7zr.SevenZipFile(file_path, mode="r") as archive:
                                    archive.extractall(path=f"{self.ukcp_location}\\Data\\Sector")

                                # Clean up artifacts
                                os.remove(file_path)
                                # Clean up old sector files
                                ext = ["ese", "rwy", "sct"]
                                sf_split = str(sf).split("\\", maxsplit=1)[-1]
                                logger.debug(f"Sector file name {sf_split}")
                                for i_ext in ext:
                                    os.remove(f"{self.ukcp_location}\\Data\\Sector\\"
                                            f"{str(sf_split).split('.', maxsplit=1)[0]}.{i_ext}")

                                # Return the newly downloaded sector file
                                loop = False
                                return str(f"{self.ukcp_location}\\Data\\Sector\\UK_{airac_format}.sct")
                        loop = False
                        return str(sf)
                    elif str(sf).split("\\", maxsplit=1)[-1] in sector_file_list:
                        logger.debug(f"{sf} validated as part of UKCP sector file")
                    else:
                        logger.warning(f"{sf} could not be validated! {sector_file}")

        sct_file = get_sector_file()
        if sct_file:
            sct_file_split = sct_file.split("\\")
        else:
            raise ValueError("Sector file couldn't be found")

        @iter_files(".asr", "r+")
        def asr_sector_file(lines=None, file=None, file_path=None):
            """Updates all 'asr' files to include the latest sector file"""

            sector_file = f"SECTORFILE:{sct_file}"
            sector_title = f"SECTORTITLE:{sct_file_split[-1]}"

            sf_replace = sector_file.replace("\\", "\\\\")

            chk = False
            if lines and file:
                for line in lines:
                    # Add the sector file path
                    content = re.sub(r"^SECTORFILE\:(.*)", sf_replace, line)

                    # If no replacement is made then try the sector title
                    if content == line:
                        content = re.sub(r"^SECTORTITLE\:(.*)", sector_title, line)

                    if content != line:
                        chk = True

                    # Write the updated content back to the file
                    file.write(content)
                file.truncate()

                # If no changes have been made, add the SECTORFILE and SECTORTITLE lines
                if not chk:
                    file.close()
                    with open(file_path, "a", encoding="utf-8") as file_append:
                        file_append.write(sector_file + "\n")
                        file_append.write(sector_title + "\n")

        @iter_files(".prf", "r+")
        def prf_files(lines=None, file=None, file_path=None):
            """Updates all 'prf' files to include the latest sector file"""

            sector_file = f"Settings\tsector\t{sct_file}"

            sf_replace = sector_file.replace("\\", "\\\\")
            if not lines or not file:
                raise ValueError("Needs all 3 parts to be passed")

            plugin_count = set()
            for line in lines:
                # Add the sector file path
                content = re.sub(r"^Settings\tsector\t(.*)", sf_replace, line)

                # Write the updated content back to the file
                file.write(content)

                # See if this line relates to plugins and determine what number they go up to
                # This is only applied on a fresh pull
                plugin_chk = re.match(r"^Plugins\tPlugin([\d]{1})\t.*", line)
                if plugin_chk:
                    plugin_count.add(plugin_chk.group(1))

            logger.trace(f"Plugin count set: {sorted(plugin_count)}")
            file.truncate()

            # Append user settings to the file
            file.close()
            with open(file_path, "a", encoding="utf-8") as file_append:
                apply_settings = []
                # Session settings
                apply_settings.append(f"LastSession\trealname\t{settings_prf['realname']}")
                apply_settings.append(f"LastSession\tcertificate\t{settings_prf['certificate']}")
                apply_settings.append(f"LastSession\tpassword\t{settings_prf['password']}")
                # apply_settings.append(f"LastSession\tfacility\t{settings_prf['facility']}")
                apply_settings.append(f"LastSession\trating\t{settings_prf['rating']}")

                # Plugin settings
                start_count_plugin = int(sorted(plugin_count)[-1]) + 1
                for count, plugin_fn in enumerate(settings_prf["plugins"], start_count_plugin):
                    apply_settings.append(f"Plugins\tPlugin{count}\t{plugin_fn}")

                # VCCS settings
                apply_settings.append(f"TeamSpeakVccs\tTs3NickName\t{settings_prf['certificate']}")
                apply_settings.append("TeamSpeakVccs\tTsVccsMiniControlX\t1581")
                apply_settings.append("TeamSpeakVccs\tTsVccsMiniControlY\t198")
                if settings_prf['vccs_ptt_g2a'] is not None:
                    apply_settings.append(
                        f"TeamSpeakVccs\tTs3G2APtt\t{settings_prf['vccs_ptt_g2a']}")
                if settings_prf['vccs_ptt_g2g'] is not None:
                    apply_settings.append(
                        f"TeamSpeakVccs\tTs3G2GPtt\t{settings_prf['vccs_ptt_g2g']}")
                if ((settings_prf['vccs_playback_mode'] is not None) and
                    (settings_prf['vccs_playback_device'] is not None) and
                    (settings_prf['vccs_capture_mode'] is not None) and
                    (settings_prf['vccs_capture_device'] is not None)):
                    apply_settings.append(
                        f"TeamSpeakVccs\tPlaybackMode\t{settings_prf['vccs_playback_mode']}")
                    apply_settings.append(
                        f"TeamSpeakVccs\tPlaybackDevice\t{settings_prf['vccs_playback_device']}")
                    apply_settings.append(
                        f"TeamSpeakVccs\tCaptureMode\t{settings_prf['vccs_capture_mode']}")
                    apply_settings.append(
                        f"TeamSpeakVccs\tCaptureDevice\t{settings_prf['vccs_capture_device']}")

                file_append.write("\n")
                for setting in apply_settings:
                    file_append.write(setting + "\n")

        @iter_files(".txt", "r+")
        def txt_files(lines=None, file=None, file_path=None):
            """Updates txt (settings) files"""

            if not lines or not file or not file_path:
                logger.warning("Needs all 3 parts to be passed")
                return
            # Do this with **all** screen setting files
            if re.match(r"^.*\_APP\_Screen.txt", file_path):
                show_vccs = "m_ShowTsVccsMiniControl:1"
                for line in lines:
                    content = re.sub(r"^m\_ShowTsVccsMiniControl\:[1|0]{1}", show_vccs, line)
                    file.write(content)
                file.truncate()

            # Do this with **all** *_APP_DL.txt setting files (Departure List)
            if re.match(r"^.*\_APP\_DL.txt", file_path):
                set_squawk_ukcp = ("m_Column:ASSR:5:1:60:9000:9022:1::UK Controller Plugin:"
                                   "UK Controller Plugin:0:0.0")
                set_vfpc = ("m_Column:VFPC:5:0:1:100:9004:1:VFPC (UK):VFPC (UK):UK "
                            "Controller Plugin:0:0.0")
                set_cdm = [
                        "m_Column:EOBT:5:1:1:120:100:1:CDM Plugin:CDM Plugin:CDM Plugin:0:0.0",
                        "m_Column:E:2:1:9:0:123:1:CDM Plugin::CDM Plugin:0:0.0",
                        "m_Column:TOBT:5:1:4:121:115:1:CDM Plugin:CDM Plugin:CDM Plugin:0:0.0",
                        "m_Column:TSAT:5:1:2:0:0:1:CDM Plugin:::0:0.0",
                        "m_Column:TTOT:5:1:3:0:0:1:CDM Plugin:::0:0.0",
                        "m_Column:TSAC:5:1:5:122:104:1:CDM Plugin:CDM Plugin:CDM Plugin:0:0.0",
                        "m_Column:ASAT:5:1:6:0:0:1:CDM Plugin:::0:0.0",
                        "m_Column:ASRT:5:1:7:107:0:1:CDM Plugin:CDM Plugin::0:0.0",
                        "m_Column:CTOT:5:1:10:108:0:1:CDM Plugin:CDM Plugin::0:0.0",
                        "m_Column:STUP:7:1:9:106:0:1::CDM Plugin::0:0.0",
                    ]

                # Set the ASSR column to use ukcp squawk
                for line in lines:
                    content = re.sub(r"^m_Column:ASSR", set_squawk_ukcp, line)
                    file.write(content)
                file.truncate()

                # Add the VFPC column if requested earlier
                if self.plugin_vfpc:
                    file.seek(0)
                    lines = file.readlines()  # Read the modified content
                    file.seek(0)
                    file.truncate()  # Clear the file
                    for line in lines:
                        content = re.sub(r"^END", set_vfpc + "\nEND", line)
                        file.write(content)

                # Add the CDM columns if requested earlier
                if self.plugin_cdm:
                    file.seek(0)
                    lines = file.readlines()  # Read the modified content
                    file.seek(0)
                    file.truncate()  # Clear the file
                    for line in lines:
                        content = re.sub(r"^END", set_cdm[0], line)
                        file.write(content)
                    for count, config in enumerate(set_cdm[1:], start=1):
                        file.write(config + "\n")
                    file.write("END\n")

            # Add stored settings from earlier into txt files
            with open("local/settings.csv", "r", encoding="utf-8") as csv_in:
                data_in = csv.DictReader(csv_in)
                for row in data_in:
                    if row["filepath"].replace("/", "\\") in str(file_path):
                        logger.debug(f"Change detected: {row['data']}")

                        # Split the string by ':' and use this as a counter
                        data_count = row['data'].split(':')
                        if len(data_count) == 2:
                            search_string = f"{data_count[0]}"
                        elif len(data_count) > 2:
                            search_string = f"{data_count[0]}:{data_count[1]}"
                        else:
                            raise ValueError(
                                f"Unable to generate search string for {row['filepath']}")

                        for line in lines:
                            content = re.sub(rf"^{search_string}\:.*", row['data'], line)
                            if content != line:
                                logger.info(content.strip())
                            file.write(content)
                        file.truncate()

        logger.info("Updating references to SECTORFILE and SECTORTITLE")
        asr_sector_file()
        logger.info("Updating your login and VCCS details")
        prf_files()
        logger.info("Updating any other settings you have opted to carry over")
        txt_files()
