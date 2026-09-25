import stat

from ukcp_updater import functions


def test_sync_skips_git_folder(tmp_path):
    cache = tmp_path / "cache"
    live = tmp_path / "live"
    (cache / ".git" / "objects").mkdir(parents=True)
    (cache / ".git" / "HEAD").write_text("ref")
    (cache / "UK").mkdir()
    (cache / "UK" / "a.prf").write_text("new")

    functions.sync_cache_to_live(str(cache), str(live))

    assert not (live / ".git").exists()
    assert (live / "UK" / "a.prf").read_text() == "new"


def test_sync_removes_git_folder_left_by_older_versions(tmp_path):
    cache = tmp_path / "cache"
    live = tmp_path / "live"
    cache.mkdir()
    (cache / "a.txt").write_text("new")
    (live / ".git" / "objects").mkdir(parents=True)
    obj = live / ".git" / "objects" / "abc"
    obj.write_text("x")
    obj.chmod(stat.S_IREAD)

    functions.sync_cache_to_live(str(cache), str(live))

    assert not (live / ".git").exists()
    assert (live / "a.txt").read_text() == "new"


def test_sync_overwrites_changed_and_keeps_extra_files(tmp_path):
    cache = tmp_path / "cache"
    live = tmp_path / "live"
    cache.mkdir()
    live.mkdir()
    (cache / "a.txt").write_text("new")
    (live / "a.txt").write_text("old")
    (live / "extra.txt").write_text("mine")

    functions.sync_cache_to_live(str(cache), str(live))

    assert (live / "a.txt").read_text() == "new"
    assert (live / "extra.txt").read_text() == "mine"
