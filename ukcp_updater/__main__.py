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
from ukcp_updater import functions, github, scanner, __VERSION__

@logger.catch
def main():
    """Main function"""

    # Set debug level
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    # Intro
    os.system("cls")
    print("-" * 60)
    print(f"VATSIM UK Controller Pack Updater v{__VERSION__}")
    print("https://github.com/chssn/ukcp-updater")
    print("-" * 60)

    # Check that git is installed
    git = github.Downloader()
    if git.check_requirements():
        # Check that the repo exists, if not then clone it
        git.clone()

        # Check current settings
        update = scanner.CurrentInstallation()
        user_settings = update.user_settings()

        # Stash any changes and run 'git pull'
        functions.sync_cache_to_live(git.git_path, git.live_path)

        # Append user settings
        update.apply_settings(user_settings, {"None": None})

        # Final check before closing
        input("Update has completed. Press ENTER to close this window...")

if __name__ == "__main__":
    main()
