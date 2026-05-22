import pytest
import yaml
from pathlib import Path
from .Handler import TradeSettingsLoadHandler


@pytest.fixture
def handler():
    return TradeSettingsLoadHandler()


class TestTradeSettingsLoadHandler:

    def test_missing_settings_raises_error(self, handler, tmp_path):
        factory_dir = tmp_path / "factory"
        factory_dir.mkdir()
        data_dir = tmp_path / "data"

        handler.DATA_DIR = data_dir
        handler.SETTINGS_FILE = data_dir / "settings.yml"
        handler.AUTH_FILE = data_dir / "auth.yaml"
        handler.TEMPLATE_SETTINGS = factory_dir / "settings.yml"
        handler.TEMPLATE_AUTH = factory_dir / "auth.yaml"

        handler.TEMPLATE_SETTINGS.write_text("log_level: DEBUG\nlog_show: true\nstart: '09:15'\nstop: '15:30'\n")
        handler.TEMPLATE_AUTH.write_text("finvasia:\n  user_id: ''\n  password: ''\n  totp_secret: ''\n")

        with pytest.raises(RuntimeError, match="Configuration files missing"):
            handler.execute()

        assert (data_dir / "settings.yml").exists()
        assert (data_dir / "auth.yaml").exists()

    def test_parse_broker_from_auth(self, handler, tmp_path):
        handler.AUTH_FILE = tmp_path / "auth.yaml"
        handler.AUTH_FILE.write_text("finvasia:\n  user_id: 'u'\n  password: 'p'\n")

        result = handler._parse_broker()
        assert result == "finvasia"

    def test_parse_valid_global_settings(self, handler, tmp_path):
        settings = {
            "log_level": "INFO",
            "log_show": True,
            "start": "09:15",
            "stop": "15:30",
        }
        f = tmp_path / "settings.yml"
        with open(f, "w") as fh:
            yaml.dump(settings, fh)

        strategy_file = tmp_path / "trade_ITBEES.yml"
        strategy_file.write_text(yaml.dump({
            "trade": {
                "strategy": "ratchet",
                "base": "ITBEES",
                "symbol": "ITBEES",
                "exchange": "BSE",
                "quantity": 33,
                "start_time": "09:30",
                "stop_time": "15:00",
                "multiplier": [1, 2, 3, 5, 8, 13, 21, 33, 55],
                "perc": 0.05,
            },
            "ITBEES": {
                "exchange": "BSE",
                "tradingsymbol": "ITBEES",
            },
        }))

        handler.SETTINGS_FILE = f
        handler.AUTH_FILE = tmp_path / "auth.yaml"
        handler.AUTH_FILE.write_text("finvasia:\n  user_id: 'u'\n  password: 'p'\n  totp_secret: 't'\n")
        handler.DATA_DIR = tmp_path

        result = handler._parse_global_settings()
        assert result.log_level == "INFO"
        assert result.log_show is True

    def test_empty_strategy_list_when_no_strategy_files(self, handler, tmp_path):
        f = tmp_path / "settings.yml"
        f.write_text("log_level: DEBUG\nlog_show: true\nstart: '09:15'\nstop: '15:30'\n")
        auth = tmp_path / "auth.yaml"
        auth.write_text("finvasia:\n  user_id: 'u'\n  password: 'p'\n  totp_secret: 't'\n")

        handler.SETTINGS_FILE = f
        handler.AUTH_FILE = auth
        handler.DATA_DIR = tmp_path

        files = handler._find_strategy_files()
        assert files == []
