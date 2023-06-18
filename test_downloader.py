import os
import pytest
import random
import re
import string
import git
from unittest.mock import patch

from ukcp_updater.functions import Downloader

letters = string.ascii_letters + string.digits + string.punctuation
rnd_string = ''.join(random.choice(letters) for _ in range(64))
downloader = Downloader()

class MockDownloaderIsGitInstalledTrue(Downloader):
    def is_git_installed(self) -> bool:
        return True

class MockDownloaderIsGitInstalledFalse(Downloader):
    def is_git_installed(self) -> bool:
        return False
    
    def install_git(self) -> bool:
        return True

def test_downloader():
    assert downloader.euroscope_appdata == os.path.join(os.environ["APPDATA"], 'EuroScope')

def test_downloader_git_folder():
    dl = Downloader(git_folder=rnd_string)
    assert dl.git_folder == rnd_string

def test_downloader_branch():
    dl = Downloader(branch=rnd_string)
    assert dl.branch == rnd_string

def test_getremotetags():
    result = downloader.get_remote_tags()
    assert isinstance(result, list)

def test_checkrequirements_isgitinstalled():
    result = downloader.check_requirements()
    assert isinstance(result, bool)

def test_check_requirements_git_not_installed():
    downloader = MockDownloaderIsGitInstalledTrue()
    result = downloader.check_requirements()
    assert result is True

@pytest.fixture
def mock_downloader():
    rtn = Downloader()
    rtn.git_path = "local\\"
    return rtn

def test_check_requirements_git_installed(mock_downloader, mocker):
    mocker.patch.object(mock_downloader, 'is_git_installed', return_value=True)

    result = mock_downloader.check_requirements()
    assert result is True

def test_check_requirements_git_not_installed_user_consents(mock_downloader, mocker):
    mocker.patch.object(mock_downloader, 'is_git_installed', return_value=False)
    mocker.patch.object(mock_downloader, 'install_git', return_value=True)

    with patch('builtins.input', return_value='Y'):
        result = mock_downloader.check_requirements()
    
    assert result is True

def test_check_requirements_git_not_installed_user_declines(mock_downloader, mocker):
    mocker.patch.object(mock_downloader, 'is_git_installed', return_value=False)
    mocker.patch.object(mock_downloader, 'install_git', return_value=True)

    with patch('builtins.input', return_value='n'):
        result = mock_downloader.check_requirements()
    
    assert result is False

def test_clone_existing_folder(mock_downloader, mocker):
    mocker.patch('os.path.exists', return_value=True)

    result = mock_downloader.clone()
    assert result is True

tags = ["2023/01", "2023/02", "2023/03"]

def test_clone_new_folder(mock_downloader, mocker):
    mocker.patch('os.path.exists', side_effect=[False, True])
    mocker.patch('git.Repo.clone_from', return_value=True)
    mocker.patch.object(mock_downloader, 'get_remote_tags', return_value=tags)
    mocker.patch('git.Repo')

    result = mock_downloader.clone()
    assert result is False
    git.Repo.clone_from.assert_called_once_with(mock_downloader.repo_url, mock_downloader.git_path, branch=mock_downloader.branch)
    mock_downloader.get_remote_tags.assert_called_once()

def test_pull():
    pass

def test_drop_stash():
    pass
