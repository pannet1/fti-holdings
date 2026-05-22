import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class SymbolsLoadHandler:

    def execute(self, factory_dir: str, symbols_file: str = "symbols.yml") -> dict:
        path = Path(factory_dir) / symbols_file
        if not path.exists():
            logger.warning(f"Symbols file not found: {path}")
            return {"status": "empty", "symbols": {}}

        from toolkit.fileutils import Fileutils
        symbols = Fileutils().get_lst_fm_yml(str(path))
        if not symbols:
            logger.info(f"No symbols found in {path}")
            return {"status": "empty", "symbols": {}}

        logger.info(f"Loaded {len(symbols)} symbols from {path}")
        return {"status": "ok", "symbols": symbols}
