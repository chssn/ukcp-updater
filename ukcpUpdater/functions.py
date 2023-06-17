#!/usr/bin/env python3

# Standard Libraries
import csv
import ctypes
import datetime
import hashlib
import os
import re
import subprocess
from distutils.version import LooseVersion
from getpass import getpass
from math import floor
from tkinter import Tk
from tkinter import filedialog

# Third Party Libraries
import git
import pandas as pd
from loguru import logger

# Local Libraries

class Airac:
    """Class for general functions relating to AIRAC"""

    def __init__(self):
        # First AIRAC date following the last cycle length modification
        startDate = "2019-01-02"
        self.baseDate = datetime.date.fromisoformat(str(startDate))
        # Length of one AIRAC cycle
        self.cycleDays = 28
        # Today
        self.todayDate = datetime.datetime.now().date()

    def initialise(self, dateIn=0) -> int:
        """Calculate the number of AIRAC cycles between any given date and the start date"""
        if dateIn:
            inputDate = datetime.date.fromisoformat(str(dateIn))
        else:
            inputDate = datetime.date.today()

        # How many AIRAC cycles have occured since the start date
        diffCycles = (inputDate - self.baseDate) / datetime.timedelta(days=1)
        # Round that number down to the nearest whole integer
        numberOfCycles = floor(diffCycles / self.cycleDays)

        return numberOfCycles

    def currentCycle(self) -> str:
        """Return the date of the current AIRAC cycle"""
        def cycle(sub:int=0):
            numberOfCycles = self.initialise() - sub
            numberOfDays = numberOfCycles * self.cycleDays + 1
            currentCycle = self.baseDate + datetime.timedelta(days=numberOfDays)
            return currentCycle
        
        currentCycle = cycle()
        if currentCycle > self.todayDate:
            currentCycle = cycle(sub=1)

        logger.info("Current AIRAC Cycle is: {}", currentCycle)

        return currentCycle
    
    def currentTag(self) -> str:
        """Returns the current tag for use with git"""
        currentCycle = self.currentCycle()
        # Split the currentCycle by '-' and return in format yyyy/mm
        split_cc = str(currentCycle).split("-")
        logger.debug(f"Current tag should be {split_cc[0]}/{split_cc[1]}")

        return f"{split_cc[0]}/{split_cc[1]}"


class Downloader:
    """
    Downloads the latest version of UKCP
    """

    def __init__(self, main_branch:bool=False, git_folder:str="uk-controller-pack", branch:str="main") -> None:
        # Currently hardcoded for VATSIM UK
        self.repo_url = "https://github.com/VATSIM-UK/uk-controller-pack.git"

        # Should the app clone the bleeding edge repo or the latest stable release
        # Default is for the latest stable release
        if main_branch:
            self.tag = "main"
        else:
            self.tag = "2023/05"

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
            logger.debug(tags)
            return tags
        return []

    def check_requirements(self) -> bool:
        """Checks to see if the basic requirements are satisfied"""

        def is_git_installed() -> bool:
            try:
                # Execute the git command to check if it is recognized
                version = subprocess.check_output(['git', '--version'])
                logger.debug(f"Git is installed - {str(version.decode()).strip()}")
                return True
            except (FileNotFoundError, subprocess.CalledProcessError):
                return False
        
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

        # Test if Git is installed
        if not is_git_installed():
            logger.error("Git is not installed")
            print("For this tool to work properly, the 'git' package is required.")
            print("This tool can automatically download the 'git' package from:")
            print("\thttps://git-scm.com/download/win")
            consent = input("Are you happy for this tool to install 'git'? [Y|n] ")
            if consent:
                if install_git():
                    logger.success("Git has been installed")
                    return True
            return False
        else:
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
        repo = git.Repo(folder)
        repo.git.checkout(self.tag)
        
        return False

    def pull(self) -> bool:
        """Performs a 'git pull' operation"""
        folder = f"{self.euroscope_appdata}\\{self.git_folder}"
        if os.path.exists(folder):
            logger.info(f"Pulling changes from {self.repo_url} to {folder}")
            
            # Open the repository
            repo = git.Repo(folder)
            # Try and switch to the main branch (ie not a tag or commit)
            switch = True
            while switch:
                try:
                    repo.git.checkout(self.branch)
                    switch = False
                except git.exc.GitCommandError as err:
                    logger.warning(f"'git checkout {self.branch}' failed due to local changes not being saved... This is quite normal!")
                    commit = repo.head.commit

                    # Get the changed files
                    changed_files = [item.a_path for item in commit.diff(None)]
                    if changed_files:
                        with open("local/settings.csv", "w") as f_set:
                            f_set.write(f"filepath,data\n")
                            # Get the latest tag (local)
                            tags = self.get_remote_tags()
                            logger.info(f"Comparing local changes against tag {tags[-1]} - this will take a minute or so to do...")
                            break_flag = False
                            for file in changed_files:
                                if break_flag:
                                    break
                                # Anything except .prf which is dealt with elsewhere along with sct, rwy and ese files
                                if str(file).split(".")[-1] not in ["prf", "sct", "rwy", "ese"]:
                                    logger.trace(file)
                                    file_diff = repo.git.diff(tags[-1], file)
                                    header = False
                                    for d in str(file_diff).split("\n"):
                                        # Only look for additions not deletions
                                        chk = re.match(r"^[\+]([A-Za-z]+.*)", d)
                                        # Exclude any line starting with SECTORFILE or SECTORTITLE - it's a given these will change
                                        exclude_sector_info = re.match(r"^\+SECTOR[FILE|TITLE].*", d)
                                        # Exclude the last line as git will match it as a change if anything is appended below
                                        exclude_gnd_trail_dots = re.match(r"^\+PLUGIN:vSMR:GndTrailsDots.*", d)
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
                        logger.info("No changed files.")

            logger.debug(repo)
            logger.info(f"Requested branch was {self.branch}")
            logger.info(f"Active branch is {repo.active_branch}")

            if str(repo.active_branch) == str(self.branch):
                # Pull the latest commit
                logger.debug(f"Pull {self.repo_url}")
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
                    for t in repo.tags:
                        if t.commit == commit:
                            tag = t.name
                            break

                    if tag:
                        logger.info(f"Detached HEAD is associated with the following tag: {tag}")
                    else:
                        logger.warning("Detached HEAD is not associated with any tags.")
                else:
                    logger.info("HEAD is not detached.")

                return True
        logger.error(f"Folder {folder} was not found!")
        return False
    
    def drop_stash(self) -> None:
        """Drop the stash once upgrade completed"""

        # Open the repository
        repo = git.Repo(self.git_path)

        # Drop the stash
        if repo.head.is_valid():
            logger.debug(repo)
            logger.debug(f"git rev-parse stash@{repo.git.rev_parse('stash@{0}')}")
            stash_list = repo.git.stash("list")
            logger.debug(stash_list)
            stash_list = stash_list.split("\n")
            if stash_list:
                # Work through the list in reverse as git will 'bump' everything down
                for s in reversed(stash_list):
                    repo.git.stash("drop", str(s).split(":")[0])
                    logger.debug(f"{str(s).split(':')[0]} has been dropped")
            else:
                logger.info("No stash to delete")
                return None
        else:
            logger.error(f"Invalid response for repo head {repo} {repo.head}")
            return None
        logger.success("Stashed files have been removed")


class CurrentInstallation:
    """
    Actions to be carried on the current installation of UKCP
    """

    def __init__(self) -> None:
        self.ukcp_location = self.location()

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
        })

        def manual_entry(realname:bool=False, certificate:bool=False, password:bool=False, rating:bool=False, all_data:bool=True) -> None:
            """Allow manual entry of user data"""

            if realname or all_data:
                return_user_data["realname"] = input("Enter your real name or CID: ")
            
            if certificate or all_data:
                return_user_data["certificate"] = input("Enter your certificate or CID: ")
            
            if password or all_data:
                return_user_data["password"] = getpass(prompt="Enter your password: ")
            
            if rating or all_data:
                return_user_data["rating"] = input("Enter your rating: ")

        def menu_option(title:str, data_type:str, options:list) -> str:
            """Menu to select one option out of many!"""
            while True:
                print(title)
                print("-"*30)
                output = {}
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
            manual_entry(all_data=True)
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
            })

            # Iterate over files in the directory and search within each file
            for root, dirs, files in os.walk(self.ukcp_location):
                for file_name in files:
                    if file_name.endswith(".prf"):
                        file_path = os.path.join(root, file_name)
                        logger.debug(f"Found {file_path}")
                        with open(file_path, 'r') as file:
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
                        for i in list(plugins):
                            print(i)
                            response = input(f"Do you want to add this plugin? [Y|n] ")
                            if response.upper() == "N":
                                continue
                            else:
                                plugin_out.append(str(i))
                    else:
                        logger.info("No custom (non UKCP) plugins were detected")
                        plugin_out = ["No custom (non UKCP) plugins were detected"]
                    
                    return_user_data["plugins"] = plugin_out

        # Check for "None" entries
        if return_user_data["realname"] is None:
            manual_entry(realname=True)
        if return_user_data["certificate"] is None:
            manual_entry(certificate=True)
        if return_user_data["password"] is None:
            manual_entry(password=True)
        if return_user_data["rating"] is None:
            manual_entry(rating=True)

        # User information
        print("The following data will be appended to all profiles in the UK Controller Pack")
        print("This is a LOCAL operation and none of your data is transmitted away from your computer!")
        print(f"Real Name:\t\t{return_user_data['realname']}")
        print(f"Certificate:\t\t{return_user_data['certificate']}")
        print(f"Password:\t\t[NOT DISPLAYED]")
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

            sector_file = []
            for root, dirs, files in os.walk(self.ukcp_location):
                for file_name in files:
                    if file_name.endswith(".sct"):
                        sector_file.append(os.path.join(root, file_name))
            
            if len(sector_file) == 1:
                logger.info(f"Sector file found at {sector_file[0]}")
                return str(sector_file[0])
            else:
                logger.error(f"Sector file search found {len(sector_file)} files")
                logger.debug(sector_file)
                raise ValueError
        
        sct_file = get_sector_file()
        sct_file_split = sct_file.split("\\")

        @iter_files(".asr", "r+")
        def asr_sector_file(lines, file, file_path):
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
                with open(file_path, "a") as file_append:
                    file_append.write(sector_file + "\n")
                    file_append.write(sector_title + "\n")
        
        @iter_files(".prf", "r+")
        def prf_files(lines, file, file_path):
            """Updates all 'prf' files to include the latest sector file"""

            sector_file = f"Settings\tsector\t{sct_file}"

            sf_replace = sector_file.replace("\\", "\\\\")

            chk = False
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
            with open(file_path, "a") as file_append:
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
        def txt_files(lines, file, file_path):
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
                for line in lines:
                    content = re.sub(r"^m_Column:ASSR", set_squawk_ukcp, line)
                    file.write(content)
                file.truncate()
            
            # Add stored settings from earlier into txt files
            with open("local/settings.csv", "r") as csv_in:
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
        logger.info(f"Testing to see if {default_path} is valid...")

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
        language = ctypes.c_void_p()
        description = ctypes.c_wchar_p()
        description_length = ctypes.c_uint()

        version_dll.VerQueryValueW(buffer, r'\StringFileInfo\040904b0\FileVersion', ctypes.byref(description), ctypes.byref(description_length))

        # Print the description
        version_number = description.value
        logger.info(f"EuroScope version {version_number} has been found")
        return version_number
    
    def compare(self) -> bool:
        """Compare the found version against the minimum required version"""

        installed_version = self.version()
        minimum_version = self.minimum_version

        # Carry out the comparison
        if LooseVersion(installed_version) > LooseVersion(minimum_version):
            logger.success(f"Installed version of EuroScope (v{installed_version}) is compatible with this script")
            return True
        raise ValueError(f"EuroScope version (v{installed_version}) is incompatible with this application. Download the latest version from https://www.euroscope.hu/wp/installation/")
