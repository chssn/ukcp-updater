from types import SimpleNamespace

import py7zr
import pytest

from ukcp_updater import scanner


def prompt(value):
    """Stand-in for an InquirerPy prompt that returns a fixed value"""
    return lambda **kwargs: SimpleNamespace(execute=lambda: value)


@pytest.fixture
def ukcp(tmp_path, monkeypatch):
    """A CurrentInstallation pointed at an empty temp folder, skipping network checks"""
    monkeypatch.chdir(tmp_path)
    location = tmp_path / "UK"
    (location / "Data" / "Sector").mkdir(parents=True)
    install = scanner.CurrentInstallation.__new__(scanner.CurrentInstallation)
    install.ukcp_location = str(location)
    install.airac = "2026/10"
    install.sector_url = "http://example.invalid/"
    return install


def settings(**overrides):
    base = {"realname": "Joe", "certificate": 1234567, "password": "pw", "rating": 5,
            "plugins": []}
    base.update(overrides)
    return base


def test_missing_password_prompts_instead_of_writing_empty_set(ukcp, monkeypatch):
    prf = scanner.os.path.join(ukcp.ukcp_location, "a.prf")
    with open(prf, "w", encoding="utf-8") as file:
        file.write("LastSession\trealname\tJoe\n"
                   "LastSession\tcertificate\t1234567\n"
                   "LastSession\trating\t5\n")
    monkeypatch.setattr(scanner, "confirm", prompt(True))
    monkeypatch.setattr(scanner, "secret", prompt("typed"))
    monkeypatch.setattr("builtins.input", lambda *args: "")

    result = ukcp.user_settings()

    assert result["password"] == "typed"


def test_two_digit_rating_is_read_in_full(ukcp, monkeypatch):
    prf = scanner.os.path.join(ukcp.ukcp_location, "a.prf")
    with open(prf, "w", encoding="utf-8") as file:
        file.write("LastSession\trealname\tJoe\n"
                   "LastSession\tcertificate\t1234567\n"
                   "LastSession\tpassword\tpw\n"
                   "LastSession\trating\t10\n")
    monkeypatch.setattr(scanner, "confirm", prompt(True))
    monkeypatch.setattr("builtins.input", lambda *args: "")

    result = ukcp.user_settings()

    assert result["rating"] == "10"


def test_txt_settings_applied_once_without_duplicating_file(ukcp, tmp_path):
    sector = scanner.os.path.join(ukcp.ukcp_location, "Data", "Sector", "UK_2026_10.sct")
    open(sector, "w").close()
    screen = scanner.os.path.join(ukcp.ukcp_location, "X_APP_Screen.txt")
    with open(screen, "w") as file:
        file.write("m_ShowTsVccsMiniControl:1\nfoo:1\nbar:baz:1\n")
    (tmp_path / "local").mkdir()
    (tmp_path / "local" / "settings.csv").write_text(
        "filepath,data\n"
        "UK/X_APP_Screen.txt,foo:2\n"
        "UK/X_APP_Screen.txt,bar:baz:C:\\path\n")

    ukcp.apply_settings(settings(), {})

    with open(screen) as file:
        assert file.read() == "m_ShowTsVccsMiniControl:0\nfoo:2\nbar:baz:C:\\path\n"


def test_prf_without_plugins_starts_at_plugin0(ukcp):
    sector = scanner.os.path.join(ukcp.ukcp_location, "Data", "Sector", "UK_2026_10.sct")
    open(sector, "w").close()
    prf = scanner.os.path.join(ukcp.ukcp_location, "a.prf")
    with open(prf, "w") as file:
        file.write("Settings\tsector\told.sct\n")

    ukcp.apply_settings(settings(plugins=["C:\\x\\A.dll"]), {})

    with open(prf, encoding="utf-8") as file:
        assert "Plugins\tPlugin0\tC:\\x\\A.dll" in file.read()


def test_plugin_numbering_handles_two_digit_indexes(ukcp):
    sector = scanner.os.path.join(ukcp.ukcp_location, "Data", "Sector", "UK_2026_10.sct")
    open(sector, "w").close()
    prf = scanner.os.path.join(ukcp.ukcp_location, "a.prf")
    with open(prf, "w") as file:
        file.write("".join(f"Plugins\tPlugin{i}\tp{i}.dll\n" for i in range(12)))

    ukcp.apply_settings(settings(plugins=["C:\\x\\A.dll"]), {})

    with open(prf, encoding="utf-8") as file:
        assert "Plugins\tPlugin12\tC:\\x\\A.dll" in file.read()


def test_no_uk_sector_file_raises_instead_of_looping(ukcp):
    sector = scanner.os.path.join(ukcp.ukcp_location, "Data", "Sector", "Falkland.sct")
    open(sector, "w").close()

    with pytest.raises(ValueError, match="Sector file couldn't be found"):
        ukcp.apply_settings(settings(), {})


def test_outdated_sector_file_is_replaced_and_old_files_removed(ukcp, tmp_path, monkeypatch):
    sector_dir = scanner.os.path.join(ukcp.ukcp_location, "Data", "Sector")
    for ext in ["sct", "ese", "rwy"]:
        open(scanner.os.path.join(sector_dir, f"UK_2026_09.{ext}"), "w").close()

    # Build the archive the "server" will hand back
    new_sct = tmp_path / "UK_2026_10.sct"
    new_sct.write_text("new")
    archive_path = tmp_path / "archive.7z"
    with py7zr.SevenZipFile(archive_path, "w") as archive:
        archive.write(new_sct, "UK_2026_10.sct")
    (tmp_path / "local").mkdir()

    monkeypatch.setattr(scanner, "confirm", prompt(True))
    monkeypatch.setattr(scanner.requests, "get",
                        lambda *args, **kwargs: SimpleNamespace(content=archive_path.read_bytes()))

    ukcp.apply_settings(settings(), {})

    assert sorted(scanner.os.listdir(sector_dir)) == ["UK_2026_10.sct"]
