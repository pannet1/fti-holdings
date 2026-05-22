import logging
import time
import yaml
from pathlib import Path
from traceback import print_exc
from typing import Any, List

from app.features.state.TradeSettingsLoad.Handler import TradeSettingsLoadHandler
from app.features.state.SymbolsLoad.Handler import SymbolsLoadHandler
from app.features.state.RunStateTrack.Handler import RunStateTrackHandler
from app.features.broker.BrokerAuthenticate.Handler import BrokerAuthenticateHandler
from app.features.strategy.RatchetStrategyRun.Handler import RatchetStrategyRunHandler
from app.features.strategy.RatchetStrategyRun.Rachet import Rachet
from app.features.order.OrderManager.Handler import OrderManagerHandler

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
FACTORY_DIR = Path("factory")
AUTH_FILE = DATA_DIR / "auth.yaml"


def load_auth_credentials(auth_file: Path, broker: str) -> dict:
    with open(auth_file) as f:
        raw = yaml.safe_load(f)
    return raw[broker]


def build_strategies(tracker: Any) -> List[Rachet]:
    instances: List[Rachet] = []
    while True:
        next_run = tracker.execute()
        if next_run["status"] == "empty":
            break
        cfg = next_run["settings"]
        try:
            strat = Rachet(**cfg)
            instances.append(strat)
            logger.info(f"Loaded strategy {strat.strategy} for {strat._tradingsymbol}")
        except Exception as e:
            logger.error(f"Failed to load strategy: {e}")
    return instances


def fetch_quotes(broker_session: Any, strategies: List[Rachet]) -> dict:
    quotes: dict = {}
    for strat in strategies:
        token = strat._token
        exchange = strat._exchange
        if token and exchange:
            try:
                result = broker_session.get_quotes(exchange, token)
                quotes[strat._tradingsymbol] = result
            except Exception as e:
                logger.error(f"Quote fetch failed for {strat._tradingsymbol}: {e}")
                quotes[strat._tradingsymbol] = 0
        else:
            quotes[strat._tradingsymbol] = 0
    return quotes


def route_signal(order_manager: OrderManagerHandler, signal: dict, broker_session: Any) -> None:
    order_manager.execute(
        tradingsymbol=signal["tradingsymbol"],
        exchange=signal["exchange"],
        transaction_type=signal["action"],
        quantity=signal["quantity"],
        price=signal["price"],
        broker_session=broker_session,
    )


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
        logger.info(f"Session authenticated: {auth['status']}")

        symbols = SymbolsLoadHandler().execute(factory_dir=str(FACTORY_DIR))
        logger.info(f"Symbols loaded: {len(symbols.get('symbols', {}))}")

        runner = RatchetStrategyRunHandler()
        tracker = RunStateTrackHandler(data_dir=str(DATA_DIR))
        order_mgr = OrderManagerHandler()

        strategies = build_strategies(tracker)
        logger.info(f"Active strategies: {len(strategies)}")

        while True:
            try:
                quotes = fetch_quotes(broker_session, strategies)

                for strategy in strategies:
                    signal = runner.execute_tick(strategy=strategy, quotes=quotes)
                    if signal is not None:
                        logger.info(f"Signal: {signal['action']} {signal['tradingsymbol']} @ {signal['price']}")
                        route_signal(order_mgr, signal, broker_session)

                time.sleep(1)

            except KeyboardInterrupt:
                logger.info("Shutdown requested")
                break

        logger.info("=== FTI Holdings: Done ===")

    except Exception as e:
        logger.error(f"Fatal: {e}")
        print_exc()


if __name__ == "__main__":
    main()
