"""
UKCP Updater
Chris Parkinson (@chssn)
"""

#!/usr/bin/env python3

# Standard Libraries
import csv
import ctypes
import datetime
import math
import os
import re
import subprocess
from getpass import getpass
from tkinter import Tk
from tkinter import filedialog
from packaging.version import Version

# Third Party Libraries
import git
import py7zr
import requests
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


class Downloader:
    """
    Downloads the latest version of UKCP
    """

    def __init__(self, git_folder:str="uk-controller-pack", branch:str="main") -> None:
        # Currently hardcoded for VATSIM UK
        self.repo_url = "https://github.com/VATSIM-UK/uk-controller-pack.git"

        # Get the current AIRAC
        airac = Airac()
        self.airac = airac.current_tag()

        # Where should the app download to?
        # Default is the EuroScope folder in APPDATA
        appdata_folder = os.environ["APPDATA"]
        self.euroscope_appdata = os.path.join(appdata_folder, 'EuroScope')
        logger.debug(f"Euroscope AppData Folder: {self.euroscope_appdata}")

        # Set some git vars
        self.git_folder = git_folder
        self.git_path = f"{self.euroscope_appdata}\\{git_folder}"
        self.branch = branch

    def get_remote_tags(self) -> list:
        """Gets a list of remote tags"""

        if os.path.exists(self.git_path):
            repo = git.Repo(self.git_path)
            tags = [tag.name for tag in repo.tags]
            logger.debug(f"Returned tags: {tags}")
            return tags
        return []

    @staticmethod
    def is_git_installed() -> bool:
        """Checks to see if the git package is installed"""
        try:
            # Execute the git command to check if it is recognized
            version = subprocess.check_output(['git', '--version'])
            logger.debug(f"Git is installed - {str(version.decode()).strip()}")
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False

    @staticmethod
    def install_git() -> bool:
        """Trys to install the git package"""
        logger.info("Lauching PowerShell to run the following command: winget install --id Git.Git -e --source winget")
        logger.info("You can find out more about winget here - https://learn.microsoft.com/en-us/windows/package-manager/winget/")

        # Launch the shell
        process = subprocess.Popen(["powershell.exe", "-Command", "winget install --id Git.Git -e --source winget"])

        # Wait for the process to complete and get the exit status
        process.communicate()
        exit_status = process.returncode

        # Continue with the remaining code or perform actions based on the exit status
        if exit_status == 0:
            logger.success("PowerShell command executed successfully.")
            return True
        else:
            logger.error("PowerShell command failed with exit status:", exit_status)
            return False

    def check_requirements(self) -> bool:
        """Checks to see if the basic requirements are satisfied"""

        # Test if EuroScope is installed
        es_check = Euroscope()
        if es_check.compare():
            # Test if Git is installed
            if not self.is_git_installed():
                logger.error("Git is not installed")
                print("For this tool to work properly, the 'git' package is required.")
                print("This tool can automatically download the 'git' package from:")
                print("\thttps://git-scm.com/download/win")
                consent = input("Are you happy for this tool to install 'git'? [Y|n] ")
                if consent.upper() == "Y" or consent is None:
                    logger.success("User has constented to the 'git' package being installed")
                    if self.install_git():
                        logger.success("Git has been installed")
                        return True
                logger.error("User has not consented to the 'git' package being installed")
                return False
        return True

    def clone(self) -> bool:
        """Perform the clone operation. Returns TRUE if the folder already exists and FALSE if not"""
        folder = f"{self.git_path}"
        if os.path.exists(folder):
            logger.success(f"The repo has already been cloned to {folder}")
            return True
        else:
            logger.info(f"Cloning into {self.repo_url}")
            git.Repo.clone_from(self.repo_url, folder, branch=self.branch)
            logger.success("The repo has been successfully cloned")

            # Checkout the latest tag
            tags = self.get_remote_tags()
            logger.debug(f"Returned tags: {tags}")
            logger.info(f"Checking out {tags[-1]}")
            repo = git.Repo(folder)
            repo.git.checkout(tags[-1])

        return False

    def pull(self) -> bool:
        """Performs a 'git pull' operation"""
        folder = f"{self.euroscope_appdata}\\{self.git_folder}"
        if os.path.exists(folder):
            logger.info(f"Pulling changes from {self.repo_url} to {folder}")

            # Open the repository
            repo = git.Repo(folder)
            # Try and switch to the main branch (ie not a tag or commit)
            try:
                repo.git.checkout(self.branch)
            except git.exc.GitCommandError:
                logger.warning(f"'git checkout {self.branch}' failed due to local changes not being saved... This is quite normal!")

                # Get the changed files
                changed_files = [item.a_path for item in repo.index.diff(None)]
                if changed_files:
                    with open("local/settings.csv", "w", encoding="utf-8") as f_set:
                        f_set.write("filepath,data\n")
                        # Get the latest tag (local)
                        tags = self.get_remote_tags()
                        logger.info(f"Comparing local changes against tag {tags[-1]} - this will take a minute or so to do...")
                        break_flag = False
                        for file in changed_files:
                            if break_flag:
                                break
                            # Anything except .prf which is dealt with elsewhere along with sct, rwy and ese files
                            if str(file).rsplit(".", maxsplit=1)[-1] not in ["prf", "sct", "rwy", "ese"] and os.path.exists(file):
                                logger.trace(file)
                                file_diff = repo.git.diff(tags[-1], file)
                                header = False
                                for d_file in str(file_diff).split("\n"):
                                    # Only look for additions not deletions
                                    chk = re.match(r"^[\+]([A-Za-z]+.*)", d_file)
                                    # Exclude any line starting with SECTORFILE or SECTORTITLE - it's a given these will change
                                    exclude_sector_info = re.match(r"^\+SECTOR[FILE|TITLE].*", d_file)
                                    # Exclude the last line as git will match it as a change if anything is appended below
                                    exclude_gnd_trail_dots = re.match(r"^\+PLUGIN:vSMR:GndTrailsDots.*", d_file)
                                    if chk and not exclude_sector_info and not exclude_gnd_trail_dots:
                                        if not header:
                                            logger.info(file)
                                            header = True
                                        logger.success(f"Change identified: {chk.group(1)}")
                                        add_setting = input("Do you want to retain this setting? [y]es | [N]o | [s]kip file | skip [a]ll: ")
                                        if add_setting.upper() == "Y":
                                            f_set.write(f"{file},{chk.group(1)}\n")
                                        elif add_setting.upper() == "S":
                                            break
                                        elif add_setting.upper() == "A":
                                            break_flag = True
                                            break

                        logger.info("Stashing changes in local repository...")
                        repo.git.stash()
                        logger.success(repo.git.rev_parse("stash@{0}"))
                else:
                    logger.info(f"No changed files. {changed_files}")

            logger.debug(repo)
            logger.info(f"Requested branch was {self.branch}")
            try:
                active_branch = repo.active_branch
                logger.info(f"Active branch is {active_branch}")
                if str(repo.active_branch) == str(self.branch):
                    # Pull the latest commit
                    logger.debug(f"Pull {self.repo_url}")
                    repo.git.stash("save", f"stashed files for {self.airac}")
                    repo.git.pull()

                    # Checkout the latest tag
                    tags = self.get_remote_tags()
                    logger.info(f"Checking out {tags[-1]}")
                    repo.git.checkout(tags[-1])

                    # Verify that we have the latest tag
                    if repo.head.is_detached:
                        commit = repo.head.commit

                        # Find the tags associated with the commit
                        tag = None
                        for r_tag in repo.tags:
                            if r_tag.commit == commit:
                                tag = r_tag.name
                                break

                        if tag:
                            logger.info(f"Detached HEAD is associated with the following tag: {tag}")
                        else:
                            logger.warning("Detached HEAD is not associated with any tags.")
                    else:
                        logger.info("HEAD is not detached.")

                    return True
            except TypeError as e:
                logger.warning(f"Cannot determine active branch: {e}")

        logger.error(f"Folder {folder} was not found!")
        return False

    def drop_stash(self) -> None:
        """Drop the stash once upgrade completed"""

        # Open the repository
        repo = git.Repo(self.git_path)

        # Check if the repo head is valid
        if not repo.head.is_valid():
            logger.error(f"Invalid response for repo head {repo} {repo.head}")
            return None

        logger.debug(repo)

        # Get the stash list
        stash_list = repo.git.stash("list")
        logger.debug(f"Stash list: {stash_list}")

        # Split the stash list into individual stashes
        stash_list = stash_list.split("\n")

        if stash_list and stash_list[0]:
            # Work through the list in reverse as git will 'bump' everything down
            for stash in reversed(stash_list):
                stash_id = str(stash).split(":", maxsplit=1)[0]
                try:
                    repo.git.stash("drop", stash_id)
                    logger.debug(f"Stash {stash_id} has been dropped")
                except git.exc.GitCommandError as e:
                    logger.error(f"Failed to drop stash {stash_id}: {e}")
        else:
            logger.info("No stash to delete")
            return None

    logger.success("All stashed files have been removed")


class CurrentInstallation:
    """
    Actions to be carried on the current installation of UKCP
    """

    def __init__(self) -> None:
        self.ukcp_location = self.location()

        # Get the current AIRAC cycle
        airac = Airac()
        self.airac = airac.current_tag()

        # Sector file base URL
        self.sector_url = "http://www.vatsim.uk/files/sector/esad/"

        # Set some vars to do with specific plugins
        self.plugin_vfpc = False
        self.plugin_cdm = False

    @staticmethod
    def location() -> str:
        """Find the current location of UKCP"""

        # This is the default install location for EuroScope
        appdata_folder = os.environ["APPDATA"]
        default_path = os.path.join(appdata_folder, 'EuroScope', 'uk-controller-pack', 'UK')
        logger.debug(f"Testing to see if {default_path} is valid...")

        if os.path.exists(default_path):
            logger.debug(f"UK Controller Pack data is installed in the default location {default_path}")
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
    def manual_entry(return_user_data:dict, realname:bool=False, certificate:bool=False, password:bool=False, rating:bool=False, all_data:bool=True) -> dict:
        """Allow manual entry of user data"""

        if realname or all_data:
            return_user_data["realname"] = input("Enter your real name or CID: ")

        if certificate or all_data:
            data_cid = "None"
            while not re.match(r"[\d]{6,8}", data_cid):
                data_cid = input("Enter your certificate or CID: ")
            return_user_data["certificate"] = data_cid

        if password or all_data:
            return_user_data["password"] = getpass(prompt="Enter your password: ")

        if rating or all_data:
            data_rating = "None"
            while not re.match(r"[\d]{1}", data_rating):
                data_rating = input("Enter your rating: ")
            return_user_data["rating"] = data_rating

        return return_user_data

    def user_settings(self) -> dict:
        """Parse current *.prf files for custom settings"""

        plugin_out = []
        return_user_data = {}
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
            while True:
                print(title)
                print("-"*30)
                output = {}
                number = 0
                for number, item in enumerate(options, start=1):
                    print(f"{number}.\t{item}")
                    output[int(number)] = item

                print(f"n.\tEnter new {data_type}")
                logger.debug(f"{data_type} menu options are {output}")

                choice = input(f"Please select which {data_type} you wish to use in all profiles: ")
                if re.match(r"[nN0-9]{1,}", choice):
                    if choice.upper() == "N":
                        return input(f"Enter the new {data_type}: ")
                    elif int(choice) >= 1 and int(choice) <= int(number):
                        return output[int(choice)]
                else:
                    logger.error(f"Invalid input detected, you entered {choice}. Please enter the number corresponding to the option you wish to use")

        # Ask the user if they consent to file search for custom settings
        consent = input("Do you want us to search your existing files for any custom settings? [Y|n] ")
        if consent.upper() == "N":
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
                "plugins": r"Plugins\tPlugin[0-9]{1}\t([A-Z]{1}\:\\.*)",
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
                        menu_select = menu_option(f"Select the {key} you wish to use below", key, list(values))
                        return_user_data[key] = menu_select
                    else:
                        return_user_data[key] = next(iter(values), None)
                elif key == "password":
                    # Passwords handled separately
                    if len(values) > 1:
                        logger.warning("More than one setting for your password has been found!")
                        logger.info(f"We found {len(values)} different passwords however won't display them!")
                        logger.info("Please enter your password below. Note that no characters or *'s will be displayed!")
                        return_user_data["password"] = getpass()
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
                                # If the VFPC plugin is going to be used then set the environmental variable
                                if re.match(r".*VFPC\.dll", plugin):
                                    logger.debug("VFPC.dll specific functions enabled")
                                    self.plugin_vfpc = True
                                # If the CDM plugin is going to be used then set the environmental variable
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
        print("This is a LOCAL operation and none of your data is transmitted away from your computer!")
        print(f"Real Name:\t\t{return_user_data['realname']}")
        print(f"Certificate:\t\t{return_user_data['certificate']}")
        print("Password:\t\t[NOT DISPLAYED]")
        print(f"Rating:\t\t\t{return_user_data['rating']}")
        for j, i in enumerate(plugin_out):
            if j == 0:
                print(f"Plugins:\t\t{i}")
            else:
                print(f"\t\t\t{i}")
        print(f"VCCS Nickname:\t\t{return_user_data['certificate']}\t\tnote: this has just been copied from your certificate")
        print(f"VCCS G2A PTT:\t\t{return_user_data['vccs_ptt_g2a']}\t\tnote: this is a scancode representation of a phyiscal key")
        print(f"VCCS G2G PTT:\t\t{return_user_data['vccs_ptt_g2g']}\t\tnote: this is a scancode representation of a phyiscal key")
        print(f"VCCS Capture Mode:\t{return_user_data['vccs_capture_mode']}")
        print(f"VCCS Playback Mode:\t{return_user_data['vccs_playback_mode']}")
        print(f"VCCS Capture Mode:\t{return_user_data['vccs_capture_device']}")
        print(f"VCCS Playback Mode:\t{return_user_data['vccs_playback_device']}")
        print("Hoppies CPDLC Password:\t[NOT DISPLAYED]")
        input("Press ENTER to continue...")

        return return_user_data

    def apply_settings(self, settings_prf:dict, settings_asr:dict) -> bool:
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

        def get_sector_file() -> str:
            """Get the sector file name"""

            loop = True
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
                if len(sector_file) == 1 and len(sector_fn) == 1:
                    logger.info(f"Sector file found at {sector_file[0]}")

                    # Check the sector file matches the current AIRAC cycle
                    airac_format = str(self.airac.replace("/", "_"))
                    if airac_format not in sector_file[0]:
                        logger.warning(f"Your sector file appears out of date with the current {self.airac} release!")
                        dl_sector = input("Would you like to download the latest sector file? [Y|n] ")
                        if str(dl_sector).upper() != "N":
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
                            logger.debug(f"Sector file name{sector_fn}")
                            for i_ext in ext:
                                os.remove(f"{self.ukcp_location}\\Data\\Sector\\{str(sector_fn[0]).split('.', maxsplit=1)[0]}.{i_ext}")

                            # Return the newly downloaded sector file
                            loop = False
                            return str(f"{self.ukcp_location}\\Data\\Sector\\UK_{airac_format}.sct")
                    loop = False
                    return str(sector_file[0])
                else:
                    logger.warning(f"Sector file search found {len(sector_file)} files. You should only have one of these!")
                    logger.debug(sector_file)
                    if len(sector_file) > 1:
                        # Delete all sector file data and re-download
                        ext = ["ese", "rwy", "sct"]
                        logger.debug(f"Sector file name{sector_fn}")
                        for i_ext in ext:
                            os.remove(f"{self.ukcp_location}\\Data\\Sector\\{str(sector_fn[0]).split('.', maxsplit=1)[0]}.{i_ext}")

        sct_file = get_sector_file()
        sct_file_split = sct_file.split("\\")

        @iter_files(".asr", "r+")
        def asr_sector_file(lines=None, file=None, file_path=None):
            """Updates all 'asr' files to include the latest sector file"""

            sector_file = f"SECTORFILE:{sct_file}"
            sector_title = f"SECTORTITLE:{sct_file_split[-1]}"

            sf_replace = sector_file.replace("\\", "\\\\")

            chk = False
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
                    apply_settings.append(f"TeamSpeakVccs\tTs3G2APtt\t{settings_prf['vccs_ptt_g2a']}")
                if settings_prf['vccs_ptt_g2g'] is not None:
                    apply_settings.append(f"TeamSpeakVccs\tTs3G2GPtt\t{settings_prf['vccs_ptt_g2g']}")
                if (settings_prf['vccs_playback_mode'] is not None) and (settings_prf['vccs_playback_device'] is not None) and (settings_prf['vccs_capture_mode'] is not None) and (settings_prf['vccs_capture_device'] is not None):
                    apply_settings.append(f"TeamSpeakVccs\tPlaybackMode\t{settings_prf['vccs_playback_mode']}")
                    apply_settings.append(f"TeamSpeakVccs\tPlaybackDevice\t{settings_prf['vccs_playback_device']}")
                    apply_settings.append(f"TeamSpeakVccs\tCaptureMode\t{settings_prf['vccs_capture_mode']}")
                    apply_settings.append(f"TeamSpeakVccs\tCaptureDevice\t{settings_prf['vccs_capture_device']}")

                file_append.write("\n")
                for setting in apply_settings:
                    file_append.write(setting + "\n")

        @iter_files(".txt", "r+")
        def txt_files(lines=None, file=None, file_path=None):
            """Updates txt (settings) files"""

            # Do this with **all** screen setting files
            if re.match(r"^.*\_APP\_Screen.txt", file_path):
                show_vccs = "m_ShowTsVccsMiniControl:1"
                for line in lines:
                    content = re.sub(r"^m\_ShowTsVccsMiniControl\:[1|0]{1}", show_vccs, line)
                    file.write(content)
                file.truncate()

            # Do this with **all** *_APP_DL.txt setting files (Departure List)
            if re.match(r"^.*\_APP\_DL.txt", file_path):
                set_squawk_ukcp = "m_Column:ASSR:5:1:60:9000:9022:1::UK Controller Plugin:UK Controller Plugin:0:0.0"
                set_vfpc = "m_Column:VFPC:5:0:1:100:9004:1:VFPC (UK):VFPC (UK):UK Controller Plugin:0:0.0"
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
                            logger.error(f"Unable to generate search string for {row['filepath']}")

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

        version_dll.VerQueryValueW(buffer, r'\StringFileInfo\040904b0\FileVersion', ctypes.byref(description), ctypes.byref(description_length))

        # Print the description
        version_number = description.value
        logger.debug(f"EuroScope version {version_number} has been found")
        return version_number

    def compare(self) -> bool:
        """Compare the found version against the minimum required version"""

        installed_version = self.version()
        minimum_version = self.minimum_version

        # Carry out the comparison
        if Version(installed_version) > Version(minimum_version):
            logger.success(f"Installed version of EuroScope (v{installed_version}) is compatible with this script")
            return True
        raise ValueError(f"EuroScope version (v{installed_version}) is incompatible with this application. Download the latest version from https://www.euroscope.hu/wp/installation/")
