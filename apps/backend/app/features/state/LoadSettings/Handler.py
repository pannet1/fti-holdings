import logging
import shutil
from pathlib import Path
from typing import List

import yaml
from pydantic import ValidationError

from .Schema import GlobalSettings, StrategySettings

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
REPO_ROOT = BACKEND_ROOT.parent.parent
DATA_DIR = REPO_ROOT / "data"
FACTORY_DIR = BACKEND_ROOT / "factory"


class LoadSettingsHandler:

    def __init__(self) -> None:
        self.DATA_DIR = DATA_DIR
        self.FACTORY_DIR = FACTORY_DIR
        self.SETTINGS_FILE = DATA_DIR / "settings.yml"
        self.AUTH_FILE = DATA_DIR / "auth.yaml"
        self.TEMPLATE_SETTINGS = FACTORY_DIR / "settings.yml"
        self.TEMPLATE_AUTH = FACTORY_DIR / "auth.yaml"

    def execute(self) -> dict:
        self._ensure_data_dir()
        missing = self._check_config_files()

        if missing:
            self._scaffold_templates(missing)
            names = ", ".join(m.name for m in missing)
            msg = (
                f"Configuration files missing: {names}. "
                f"Templates copied to data/. Fill them in and re-run."
            )
            logger.error(msg)
            raise RuntimeError(msg)

        broker = self._parse_broker()
        global_settings = self._parse_global_settings()
        strategy_files = self._find_strategy_files()
        strategies = [s for f in strategy_files if (s := self._parse_strategy_file(f)) is not None]

        return {
            "broker": broker,
            "global": global_settings.model_dump(),
            "strategies": [s.model_dump() for s in strategies],
        }

    def _ensure_data_dir(self) -> None:
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _check_config_files(self) -> List[Path]:
        missing = []
        if not self.SETTINGS_FILE.exists():
            missing.append(self.TEMPLATE_SETTINGS)
        if not self.AUTH_FILE.exists():
            missing.append(self.TEMPLATE_AUTH)
        return missing

    def _scaffold_templates(self, missing: List[Path]) -> None:
        for tmpl in missing:
            if not tmpl.exists():
                msg = f"Factory template not found: {tmpl}. Cannot scaffold config files."
                logger.critical(msg)
                raise RuntimeError(msg)
            dst = self.DATA_DIR / tmpl.name
            shutil.copy2(str(tmpl), str(dst))
            logger.info(f"Copied {tmpl.name} -> {dst}")

    def _parse_broker(self) -> str:
        with open(self.AUTH_FILE) as f:
            raw = yaml.safe_load(f)
        keys = list(raw.keys())
        if not keys:
            raise ValueError("auth.yaml is empty")
        return keys[0]

    def _parse_global_settings(self) -> GlobalSettings:
        with open(self.SETTINGS_FILE) as f:
            raw = yaml.safe_load(f)
        try:
            return GlobalSettings(**raw)
        except ValidationError as e:
            logger.error(f"Invalid settings.yml: {e}")
            raise

    def _find_strategy_files(self) -> List[Path]:
        exclude = {"settings.yml", "auth.yaml", "auth.yml"}
        return [
            p for p in self.DATA_DIR.glob("*.yml")
            if p.name not in exclude
        ]

    def _parse_strategy_file(self, path: Path) -> StrategySettings | None:
        with open(path) as f:
            raw = yaml.safe_load(f)
        if isinstance(raw, dict):
            candidates = [v for v in raw.values() if isinstance(v, dict) and "strategy" in v]
            if candidates:
                raw = candidates[0]
        try:
            return StrategySettings(**raw)
        except ValidationError:
            logger.warning(f"Skipping {path.name}: not a valid strategy config")
            return None
