import pytest
from pathlib import Path

from .Handler import TrackRunStateHandler


class TestTrackRunStateHandler:

    def test_empty_run_state_returns_empty_set(self, tmp_path):
        handler = TrackRunStateHandler(str(tmp_path))
        assert handler._get_run_state() == set()

    def test_save_and_read_state(self, tmp_path):
        handler = TrackRunStateHandler(str(tmp_path))
        handler._save_state("nifty.yml")
        handler._save_state("banknifty.yml")
        assert handler._get_run_state() == {"nifty.yml", "banknifty.yml"}

    def test_find_next_strategy_returns_none_when_empty(self, tmp_path):
        handler = TrackRunStateHandler(str(tmp_path))
        assert handler._find_next_strategy() is None

    def test_find_next_ignores_settings_yml(self, tmp_path):
        (tmp_path / "settings.yml").write_text("key: val")
        (tmp_path / "nifty.yml").write_text("key: val")
        handler = TrackRunStateHandler(str(tmp_path))
        assert handler._find_next_strategy() == "nifty.yml"

    def test_skips_already_run_strategies(self, tmp_path):
        (tmp_path / "nifty.yml").write_text("key: val")
        (tmp_path / "banknifty.yml").write_text("key: val")
        handler = TrackRunStateHandler(str(tmp_path))
        handler._save_state("nifty.yml")
        assert handler._find_next_strategy() == "banknifty.yml"

    def test_execute_returns_empty_when_all_run(self, tmp_path):
        handler = TrackRunStateHandler(str(tmp_path))
        result = handler.execute()
        assert result["status"] == "empty"
