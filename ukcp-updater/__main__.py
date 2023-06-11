#!/usr/bin/env python3

# Standard Libraries

# Third Party Libraries
from loguru import logger

# Local Libraries
from . import functions

@logger.catch
def main():
    # Check that git is installed
    git = functions.Downloader()
    if git.check_requirements():
        # Check that the repo exists, if not then clone it
        git.clone()

        # Check current settings
        update = functions.CurrentInstallation()
        user_settings = update.user_settings()
        changed_files = update.hash_compute()

        # Stash any changes and run 'git pull'
        git.pull()

if __name__ == "__main__":
    main()