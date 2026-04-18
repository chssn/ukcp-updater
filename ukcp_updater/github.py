"""
UKCP Updater
Chris Parkinson (@chssn)
"""

#!/usr/bin/env python3

# Standard Libraries
import os
import subprocess

# Third Party Libraries
import git
from InquirerPy.inquirer import confirm # type: ignore
from loguru import logger

# Local Libraries
from ukcp_updater import airac, euroscope


class Downloader:
    """
    Downloads the latest version of UKCP
    """

    def __init__(self, cache:str="ukcp-cache", live:str="ukcp-live" , branch:str="main") -> None:
        # Currently hardcoded for VATSIM UK
        self.repo_url = "https://github.com/VATSIM-UK/uk-controller-pack.git"

        # Get the current AIRAC
        airac_init = airac.Airac()
        self.airac = airac_init.current_tag()

        # Where should the app download to?
        # Default is the EuroScope folder in APPDATA
        appdata_folder = os.environ["APPDATA"]
        self.euroscope_appdata = os.path.join(appdata_folder, 'EuroScope')
        logger.debug(f"Euroscope AppData Folder: {self.euroscope_appdata}")

        # Set some git vars
        self.git_path = f"{self.euroscope_appdata}\\{cache}"
        self.live_path = f"{self.euroscope_appdata}\\{live}"
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
        logger.info("Lauching PowerShell to run the following command: "
                    "winget install --id Git.Git -e --source winget")
        logger.info("You can find out more about winget here - "
                    "https://learn.microsoft.com/en-us/windows/package-manager/winget/")

        # Launch the shell
        process = subprocess.Popen(
            ["powershell.exe", "-Command", "winget install --id Git.Git -e --source winget"])

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
        es_check = euroscope.Euroscope()
        if es_check.compare():
            # Test if Git is installed
            if not self.is_git_installed():
                logger.error("Git is not installed")
                print("For this tool to work properly, the 'git' package is required.")
                print("This tool can automatically download the 'git' package from:")
                print("\thttps://git-scm.com/download/win")
                message = "Are you happy for this tool to install 'git'?"
                sel = confirm(message=message, default=True).execute()
                if sel:
                    logger.success("User has constented to the 'git' package being installed")
                    if self.install_git():
                        logger.success("Git has been installed")
                        return True
                logger.error("User has not consented to the 'git' package being installed")
                return False
        return True

    def clone(self) -> bool:
        """
        Perform the clone operation. Returns TRUE if the folder already exists and FALSE if not
        """

        folder = f"{self.git_path}"
        if os.path.exists(folder):
            logger.success(f"The repo has already been cloned to {folder}")
            return True
        else:
            logger.info(f"Cloning into {self.repo_url}")
            git.Repo.clone_from(self.repo_url, folder, branch=self.branch)
            logger.success("The repo has been successfully cloned")

            # Ensure that we're on the main branch
            repo = git.Repo(folder)
            repo.git.checkout(self.branch)

        return False

    def pull(self) -> bool:
        """git pull"""
        folder = self.git_path

        if not os.path.exists(folder):
            logger.error("Repo folder missing")
            return False

        repo = git.Repo(folder)

        logger.info("Fetching updates")
        repo.git.fetch("--all", "--prune")

        # If dirty, stash
        if repo.is_dirty(untracked_files=True):
            logger.info("Local changes detected, stashing")
            repo.git.stash("push", "-u", "-m", "ukcp auto-update")

        # Reset to remote
        repo.git.reset("--hard", f"origin/{self.branch}")
        repo.git.clean("-fd")

        # Reattach
        if repo.head.is_detached:
            repo.git.checkout(self.branch, force=True)

        # Pull
        repo.git.pull("origin", self.branch)

        # Checkout latest tag
        tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime)

        if tags:
            latest = tags[-1].name
            logger.info(f"Checking out tag {latest}")
            repo.git.checkout(latest)

        return True
