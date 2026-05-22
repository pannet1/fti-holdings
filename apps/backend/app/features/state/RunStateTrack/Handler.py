import logging
from pathlib import Path
from typing import Optional, Set

logger = logging.getLogger(__name__)


class RunStateTrackHandler:

    def __init__(self, data_dir: str, run_file: str = "run.txt"):
        self.data_dir = Path(data_dir)
        self.run_filepath = self.data_dir / run_file

    def _get_run_state(self) -> Set[str]:
        try:
            with open(self.run_filepath) as f:
                return {line.strip() for line in f}
        except FileNotFoundError:
            return set()

    def _save_state(self, setting_file: str):
        self.run_filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self.run_filepath, "a") as f:
            f.write(setting_file + "\n")

    def _find_next_strategy(self) -> Optional[str]:
        all_from_dir = [p.name for p in self.data_dir.glob("*.yml") if p.name != "settings.yml"]
        all_from_dir.extend(p.name for p in self.data_dir.glob("*.yaml") if p.name not in ("auth.yaml", "auth.yml"))
        sets_from_file = self._get_run_state()
        yet_to_run = [s for s in all_from_dir if s not in sets_from_file]
        yet_to_run.sort(reverse=True)
        return yet_to_run.pop() if yet_to_run else None

    def execute(self) -> dict:
        curr_set = self._find_next_strategy()
        if curr_set:
            from toolkit.fileutils import Fileutils
            self._save_state(curr_set)
            trade_settings = Fileutils().get_lst_fm_yml(str(self.data_dir / curr_set))
            logger.info(f"Loaded next strategy: {curr_set}")
            return {"status": "ok", "strategy_file": curr_set, "settings": trade_settings}
        logger.info("No pending strategies to run")
        return {"status": "empty", "strategy_file": None, "settings": None}
