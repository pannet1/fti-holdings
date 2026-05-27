import logging
from pathlib import Path
from typing import Optional, Set

import yaml

logger = logging.getLogger(__name__)


class TrackRunStateHandler:

    def __init__(self, data_dir: str, run_file: str = "run.txt") -> None:
        self.data_dir = Path(data_dir)
        self.run_filepath = self.data_dir / run_file

    def _get_run_state(self) -> Set[str]:
        try:
            with open(self.run_filepath) as f:
                return {line.strip() for line in f}
        except FileNotFoundError:
            return set()

    def _save_state(self, strategy_name: str) -> None:
        self.run_filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self.run_filepath, "a") as f:
            f.write(strategy_name + "\n")

    def _extract_strategy_name(self, filepath: Path) -> Optional[str]:
        try:
            with open(filepath) as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict):
                return None
            for v in data.values():
                if isinstance(v, dict) and "strategy" in v:
                    return str(v["strategy"])
            return None
        except Exception:
            return None

    def _find_next_strategy(self) -> Optional[str]:
        all_filepaths: list[Path] = list(self.data_dir.glob("*.yml"))
        all_filepaths.extend(self.data_dir.glob("*.yaml"))
        already_run = self._get_run_state()
        candidates: list[tuple[str, Path]] = []
        for fp in all_filepaths:
            name = fp.name
            if name in ("settings.yml", "settings.yaml", "auth.yaml", "auth.yml"):
                continue
            strategy_name = self._extract_strategy_name(fp)
            if strategy_name is not None and strategy_name not in already_run:
                candidates.append((strategy_name, fp))
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates.pop()[0] if candidates else None

    def execute(self) -> dict:
        from toolkit.fileutils import Fileutils

        curr_name = self._find_next_strategy()
        if curr_name is None:
            logger.info("No pending strategies to run")
            return {"status": "empty", "strategy_file": None, "settings": None}
        fp = None
        for p in self.data_dir.glob("*.yml"):
            if self._extract_strategy_name(p) == curr_name:
                fp = p
                break
        if fp is None:
            for p in self.data_dir.glob("*.yaml"):
                if self._extract_strategy_name(p) == curr_name:
                    fp = p
                    break
        if fp is None:
            logger.error(f"Strategy '{curr_name}' resolved but file not found")
            return {"status": "empty", "strategy_file": None, "settings": None}
        self._save_state(curr_name)
        trade_settings = Fileutils().get_lst_fm_yml(str(fp))
        logger.info(f"Loaded next strategy: {curr_name}")
        return {"status": "ok", "strategy_file": fp.name, "settings": trade_settings}
