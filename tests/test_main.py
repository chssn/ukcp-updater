from unittest.mock import MagicMock

from ukcp_updater import __main__ as app


def test_main_pulls_before_syncing(monkeypatch):
    calls = MagicMock()
    downloader = calls.downloader
    downloader.check_requirements.return_value = True
    monkeypatch.setattr(app.github, "Downloader", lambda: downloader)
    monkeypatch.setattr(app.scanner, "CurrentInstallation", MagicMock())
    monkeypatch.setattr(app.functions, "sync_cache_to_live", calls.sync)
    monkeypatch.setattr(app.os, "system", lambda cmd: 0)
    monkeypatch.setattr("builtins.input", lambda *args: "")

    app.main()

    names = [name for name, _, _ in calls.mock_calls]
    assert names.index("downloader.pull") < names.index("sync")
