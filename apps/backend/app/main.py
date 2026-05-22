import logging
import yaml
from pathlib import Path
from traceback import print_exc

from app.features.state.TradeSettingsLoad.Handler import TradeSettingsLoadHandler
from app.features.state.SymbolsLoad.Handler import SymbolsLoadHandler
from app.features.state.RunStateTrack.Handler import RunStateTrackHandler
from app.features.broker.BrokerAuthenticate.Handler import BrokerAuthenticateHandler
from app.features.strategy.RatchetStrategyRun.Handler import RatchetStrategyRunHandler

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
FACTORY_DIR = Path("factory")
AUTH_FILE = DATA_DIR / "auth.yaml"


def load_auth_credentials(auth_file: Path, broker: str) -> dict:
    with open(auth_file) as f:
        raw = yaml.safe_load(f)
    return raw[broker]


def main():
    try:
        logger.info("=== FTI Holdings: Starting ===")

        settings = TradeSettingsLoadHandler().execute()
        logger.info(f"Broker: {settings['broker']}")
        logger.info(f"Strategies found: {len(settings['strategies'])}")

        creds = load_auth_credentials(AUTH_FILE, settings["broker"])
        logger.info("Authenticating with broker...")
        auth = BrokerAuthenticateHandler().execute(
            userid=creds["userid"],
            password=creds["password"],
            totp_secret=creds["totp_secret"],
            api_key=creds.get("api_key", ""),
            api_secret=creds.get("api_secret", ""),
            imei=creds.get("imei", ""),
            oauth_url=creds.get("oauth_url", ""),
            token_path=str(DATA_DIR / f"{creds['userid']}.txt"),
            vendor_code=creds.get("vendor_code", ""),
        )
        broker_session = auth["session"]
        logger.info(f"Authenticated: {auth['status']}")

        symbols = SymbolsLoadHandler().execute(factory_dir=str(FACTORY_DIR))
        logger.info(f"Symbols loaded: {len(symbols.get('symbols', {}))}")

        runner = RatchetStrategyRunHandler()
        tracker = RunStateTrackHandler(data_dir=str(DATA_DIR))

        while True:
            next_run = tracker.execute()
            if next_run["status"] == "empty":
                logger.info("All strategies executed")
                break

            cfg = next_run["settings"]
            result = runner.execute(config=cfg, broker_session=broker_session)
            logger.info(f"Ran strategy: {result}")

        logger.info("=== FTI Holdings: Done ===")

    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    except Exception as e:
        logger.error(f"Fatal: {e}")
        print_exc()


if __name__ == "__main__":
    main()
