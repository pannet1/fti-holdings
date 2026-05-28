import logging
from pathlib import Path
from toolkit.async_logger import AsyncLogger

ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = ROOT / "data" / "log.txt"
SETTINGS_FILE = ROOT / "data" / "settings.yml"


def async_logger():
    if not LOG_FILE.parent.exists():
        LOG_FILE.parent.mkdir(parents=True)

    if SETTINGS_FILE.exists():
        import yaml
        with open(SETTINGS_FILE) as f:
            raw = yaml.safe_load(f) or {}
        level = raw.get("log_level", logging.DEBUG)
        log_show = raw.get("log_show", True)
    else:
        level = logging.DEBUG
        log_show = True

    if log_show:
        manager = AsyncLogger(level)
    else:
        manager = AsyncLogger(level, str(LOG_FILE))

    manager.start()
    logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
    logging.getLogger("websocket").setLevel(logging.WARNING)
    logging.getLogger("broker_ai.finvasia.NewNorenApi").setLevel(logging.INFO)
    return manager.get_logger_function()


logging_func = async_logger()
