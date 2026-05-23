import logging
import sys
import time
import yaml
from datetime import datetime
from pathlib import Path
from traceback import print_exc
from typing import Any, List

from app.features.state.LoadSettings.Handler import LoadSettingsHandler
from app.features.state.LoadSymbols.Handler import LoadSymbolsHandler
from app.features.state.TrackRunState.Handler import TrackRunStateHandler
from app.features.broker.AuthenticateBroker.Handler import AuthenticateBrokerHandler
from app.features.strategy.RunRatchetStrategy.Handler import RunRatchetStrategyHandler
from app.features.strategy.RunRatchetStrategy.Ratchet import Rachet
from app.features.order.Handler import ManageOrderHandler
from app.features.state.TrackHoldings.Handler import TrackHoldingsHandler
from app.features.state.TrackHoldings.Schema import HoldingsRow
from app.features.state.JournalTrades.Handler import JournalTradesHandler

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent.parent
DATA_DIR = REPO_ROOT / "data"
FACTORY_DIR = BACKEND_ROOT / "factory"
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


def route_signal(
    order_manager: ManageOrderHandler,
    signal: dict,
    broker_session: Any,
    holdings_tracker: TrackHoldingsHandler,
    trades_journal: JournalTradesHandler,
) -> None:
    result = order_manager.execute(
        tradingsymbol=signal["tradingsymbol"],
        exchange=signal["exchange"],
        transaction_type=signal["action"],
        quantity=signal["quantity"],
        price=signal["price"],
        broker_session=broker_session,
    )
    if result.get("status") == "ok":
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = HoldingsRow(
            datetime=now,
            exchange=signal["exchange"],
            tradingsymbol=signal["tradingsymbol"],
            side=signal["action"],
            avg_price=float(signal["price"]),
            quantity=int(signal["quantity"]),
            strategy="ratchet",
        )
        if signal["action"] == "BUY":
            holdings_tracker.add_holding(row)
        elif signal["action"] == "SELL":
            holdings_tracker.remove_holding(signal["tradingsymbol"], int(signal["quantity"]))
            trades_journal.journal_trade(row)


def main():
    try:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
            stream=sys.stdout,
            force=True,
        )
        logger.info("=== FTI Holdings: Starting ===")

        settings = LoadSettingsHandler().execute()
        logger.info(f"Broker: {settings['broker']}")
        logger.info(f"Strategies found: {len(settings['strategies'])}")

        creds = load_auth_credentials(AUTH_FILE, settings["broker"])
        logger.info("Authenticating with broker...")
        auth = AuthenticateBrokerHandler().execute(
            userid=creds["userid"],
            password=creds["password"],
            totp_secret=creds["totp_secret"],
            api_key=creds.get("api_key", ""),
            api_secret=creds.get("api_secret", ""),
            imei=creds.get("imei", ""),
            oauth_url=creds.get("oauth_url", ""),
            token_path=str(DATA_DIR / f"{creds['userid']}.txt"),
            vendor_code=creds.get("vendor_code", ""),
            access_token=creds.get("access_token"),
            refresh_token=creds.get("refresh_token"),
            app_key_hash=creds.get("app_key_hash"),
        )
        broker_session = auth["session"]
        logger.info(f"Session authenticated: {auth['status']}")

        symbols = LoadSymbolsHandler().execute(factory_dir=str(FACTORY_DIR))
        logger.info(f"Symbols loaded: {len(symbols.get('symbols', {}))}")

        runner = RunRatchetStrategyHandler()
        tracker = TrackRunStateHandler(data_dir=str(DATA_DIR))
        order_mgr = ManageOrderHandler()
        holdings_tracker = TrackHoldingsHandler(data_dir=str(DATA_DIR))
        trades_journal = JournalTradesHandler(data_dir=str(DATA_DIR))

        strategies = build_strategies(tracker)
        logger.info(f"Active strategies: {len(strategies)}")

        while True:
            try:
                quotes = fetch_quotes(broker_session, strategies)
                logger.info(f"Tick: {len(quotes)} quotes, {len(strategies)} strategies active")

                for strategy in strategies:
                    signal = runner.execute_tick(strategy=strategy, quotes=quotes)
                    if signal is not None:
                        logger.info(f"Signal: {signal['action']} {signal['tradingsymbol']} @ {signal['price']}")
                        route_signal(order_mgr, signal, broker_session, holdings_tracker, trades_journal)

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
