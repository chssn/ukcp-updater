#!/usr/bin/env python3

# Standard Libraries
import ctypes
import hashlib
import os
import re
import subprocess
from distutils.version import LooseVersion
from getpass import getpass
from tkinter import Tk
from tkinter import filedialog

# Third Party Libraries
import git
import pandas as pd
from loguru import logger

# Local Libraries

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
        folder = f"{self.euroscope_appdata}\\{self.git_folder}"
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
                    logger.warning(f"'git checkout {self.branch}' failed due to local changes not being saved...")
                    commit = repo.head.commit

                    # Get the changed files
                    changed_files = [item.a_path for item in commit.diff(None)]
                    if changed_files:
                        # Get the latest tag (local)
                        tags = self.get_remote_tags()
                        logger.info(f"Diff local changes against tag {tags[-1]}")
                        for file in changed_files:
                            # Anything except .prf which is dealt with elsewhere along with sct, rwy and ese files
                            if str(file).split(".")[-1] not in ["prf", "sct", "rwy", "ese"]:
                                logger.info(file)
                                file_diff = repo.git.diff(tags[-1], file)
                                for d in str(file_diff).split("\n"):
                                    # Only look for additions not deletions
                                    chk = re.match(r"^\+([A-Za-z]+.*)", d)
                                    if chk:
                                        logger.debug(chk.group(1))
                                #print(file_diff)
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

        return_user_data = {}

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
            return_user_data["realname"] = input("Enter your real name or CID: ")
            return_user_data["certificate"] = input("Enter your certificate or CID: ")
            return_user_data["password"] = getpass(prompt="Enter your password: ")
            return_user_data["rating"] = input("Enter your rating: ")
        else:
            logger.success("User consent given for file search")

            # List all the regex patterns
            patterns = {
                "realname": r"LastSession\trealname\t(.*)",
                "certificate": r"LastSession\tcertificate\t([0-9]{4,})",
                "password": r"LastSession\tpassword\t(.*)",
                "facility": r"LastSession\tfacility\t([0-9]{1})",
                "rating": r"LastSession\trating\t([0-9]{1})",
                "plugins": r"Plugins\t(Plugin[0-9]{1}\t[A-Z]{1}\:\\.*)",
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
                    else:
                        return_user_data["password"] = list(values)[0]
                elif key == "plugins":
                    # Handle plugins separately
                    plugins = return_user_data["plugins"]
                    if plugins:
                        logger.info("The following custom (non UKCP) plugins have been detected:")
                        plugin_out = []
                        for i in list(plugins):
                            p_out = str(i).split("\\")[-1]
                            logger.info(p_out)
                            plugin_out.append(str(i))
                        response = input("Do you want to add these plugins to every profile? [Y|n] ")
                        if response.upper() == "N":
                            plugin_out = ["Not selected"]
                    else:
                        logger.info("No custom (non UKCP) plugins were detected")
                        plugin_out = ["No custom (non UKCP) plugins were detected"]
            
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
        print(f"VCCS Nickname:\t\t{return_user_data['certificate']}\t\tNote: This has just been copied from your certificate")
        print(f"VCCS G2A PTT:\t\t{return_user_data['vccs_ptt_g2a']}")
        print(f"VCCS G2G PTT:\t\t{return_user_data['vccs_ptt_g2g']}")
        print(f"VCCS Capture Mode:\t{return_user_data['vccs_capture_mode']}")
        print(f"VCCS Playback Mode:\t{return_user_data['vccs_playback_mode']}")
        print(f"VCCS Capture Mode:\t{return_user_data['vccs_capture_device']}")
        print(f"VCCS Playback Mode:\t{return_user_data['vccs_playback_device']}")
        
        return return_user_data
                                

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
