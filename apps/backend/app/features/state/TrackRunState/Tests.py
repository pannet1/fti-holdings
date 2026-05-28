from .Handler import TrackRunStateHandler


class TestTrackRunStateHandler:

    def test_empty_run_state_returns_empty_set(self, tmp_path):
        handler = TrackRunStateHandler(str(tmp_path))
        assert handler._get_run_state() == set()

    def test_save_and_read_state(self, tmp_path):
        handler = TrackRunStateHandler(str(tmp_path))
        handler._save_state("ratchet")
        handler._save_state("grid")
        assert handler._get_run_state() == {"ratchet", "grid"}

    def test_find_next_strategy_returns_none_when_empty(self, tmp_path):
        handler = TrackRunStateHandler(str(tmp_path))
        assert handler._find_next_strategy() is None

    def test_find_next_ignores_settings_yml(self, tmp_path):
        (tmp_path / "settings.yml").write_text("key: val")
        (tmp_path / "ratchet.yml").write_text("trade:\n  strategy: ratchet")
        handler = TrackRunStateHandler(str(tmp_path))
        assert handler._find_next_strategy() == "ratchet"

    def test_skips_already_run_strategies(self, tmp_path):
        (tmp_path / "ratchet.yml").write_text("trade:\n  strategy: ratchet")
        (tmp_path / "grid.yml").write_text("trade:\n  strategy: grid")
        handler = TrackRunStateHandler(str(tmp_path))
        handler._save_state("ratchet")
        assert handler._find_next_strategy() == "grid"

    def test_execute_returns_empty_when_all_run(self, tmp_path):
        handler = TrackRunStateHandler(str(tmp_path))
        result = handler.execute()
        assert result["status"] == "empty"
