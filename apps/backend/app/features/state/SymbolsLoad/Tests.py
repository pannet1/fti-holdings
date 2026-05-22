import pytest
from pathlib import Path

from .Handler import SymbolsLoadHandler


class TestSymbolsLoadHandler:

    def test_returns_empty_when_file_missing(self, tmp_path):
        handler = SymbolsLoadHandler()
        result = handler.execute(factory_dir=str(tmp_path))
        assert result["status"] == "empty"
        assert result["symbols"] == {}

    def test_returns_empty_when_no_symbols(self, tmp_path):
        f = tmp_path / "symbols.yml"
        f.write_text("")
        handler = SymbolsLoadHandler()
        result = handler.execute(factory_dir=str(tmp_path))
        assert result["status"] == "empty"

    def test_accepts_custom_filename(self, tmp_path):
        f = tmp_path / "custom.yml"
        f.write_text("NIFTY:\n  token: '26000'\n")
        handler = SymbolsLoadHandler()
        result = handler.execute(factory_dir=str(tmp_path), symbols_file="custom.yml")
        assert result["status"] == "ok"
