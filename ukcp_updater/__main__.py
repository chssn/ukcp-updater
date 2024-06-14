"""
UKCP Updater
Chris Parkinson (@chssn)
"""

#!/usr/bin/env python3

# Standard Libraries
import os
import sys

# Third Party Libraries
from loguru import logger

# Local Libraries
from ukcp_updater import functions, __version__

@logger.catch
def main():
    """Main function"""

    # Set debug level
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    # Intro
    os.system("cls")
    print("-" * 60)
    print(f"VATSIM UK Controller Pack Updater v{__version__}")
    print("https://github.com/chssn/ukcp-updater")
    print("-" * 60)

    # Check that git is installed
    git = functions.Downloader()
    if git.check_requirements():
        # Check that the repo exists, if not then clone it
        git.clone()

        # Check current settings
        update = functions.CurrentInstallation()
        user_settings = update.user_settings()

        # Stash any changes and run 'git pull'
        git.pull()

        # Append user settings
        update.apply_settings(user_settings, {"None": None})

        # Drop the stashed files
        git.drop_stash()

        # Final check before closing
        input("Update has completed. Press ENTER to close this window...")

if __name__ == "__main__":
    main()
