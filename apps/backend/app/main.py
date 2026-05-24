import logging
import sys
import time
import yaml
from datetime import datetime
from pathlib import Path
from traceback import print_exc
from typing import Any, List
import pendulum as pdlm

from app.features.state.LoadSettings.Handler import LoadSettingsHandler
from app.features.state.LoadSymbols.Handler import LoadSymbolsHandler
from app.features.state.TrackRunState.Handler import TrackRunStateHandler
from app.features.broker.AuthenticateBroker.Handler import AuthenticateBrokerHandler
from app.features.strategy.RunRatchetStrategy.Handler import RunRatchetStrategyHandler
from app.features.strategy.RunRatchetStrategy.Ratchet import Rachet
from app.features.order.ManageOrder.Handler import ManageOrderHandler
from app.features.state.TrackHoldings.Handler import TrackHoldingsHandler
from app.features.state.TrackHoldings.Schema import HoldingsRow
from app.features.state.JournalTrades.Handler import JournalTradesHandler
from app.features.market.StreamQuotes.Handler import StreamQuotesHandler
from app.features.market.HistoricQuotes.Handler import HistoricQuotesHandler
from app.features.market.HistoricQuotes.Schema import HistoricQuotesConfig
from broker_ai.finvasia.symbols import Symbol as FinvasiaSymbol

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


def build_strategies(tracker: Any, global_settings: dict) -> List[Rachet]:
    instances: List[Rachet] = []
    while True:
        next_run = tracker.execute()
        if next_run["status"] == "empty":
            break
        cfg = dict(next_run["settings"])
        candidates = [v for v in cfg.values() if isinstance(v, dict) and "strategy" in v]
        if candidates:
            cfg = dict(candidates[0])
        cfg.setdefault("candle", global_settings["candle"])
        if "tradingsymbol" not in cfg and "symbol" in cfg:
            cfg["tradingsymbol"] = cfg["symbol"]
        try:
            strat = Rachet(data_dir=str(DATA_DIR), **cfg)
            instances.append(strat)
            logger.info(f"Loaded strategy {strat.strategy} for {strat._tradingsymbol}")
        except Exception as e:
            logger.error(f"Failed to load strategy: {e}")
    return instances


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
        ts = signal.get("time") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = HoldingsRow(
            datetime=ts,
            exchange=signal["exchange"],
            tradingsymbol=signal["tradingsymbol"],
            side=signal["action"],
            avg_price=float(signal["price"]),
            quantity=int(signal["quantity"]),
            strategy="ratchet",
            multiplier=signal.get("multiplier", 1),
        )
        if signal["action"] == "BUY":
            holdings_tracker.add_holding(row)
            trades_journal.journal_trade(row)
        elif signal["action"] == "SELL":
            holdings_tracker.remove_holding(
                signal["tradingsymbol"], int(signal["quantity"])
            )
            trades_journal.journal_trade(row)


def main() -> None:
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
        is_backtest = settings["global"].get("backtest", 0)
        if is_backtest:
            class MockOrderHandler:
                def execute(self, **kwargs: Any) -> dict:
                    logger.info(f"Backtest order: {kwargs.get('transaction_type')} {kwargs.get('quantity')} {kwargs.get('tradingsymbol')} @ {kwargs.get('price')}")
                    return {"status": "ok", "order_id": "backtest"}
            order_mgr = MockOrderHandler()
        else:
            order_mgr = ManageOrderHandler()
        holdings_tracker = TrackHoldingsHandler(data_dir=str(DATA_DIR))
        trades_journal = JournalTradesHandler(data_dir=str(DATA_DIR))

        strategies = build_strategies(tracker, settings["global"])
        logger.info(f"Active strategies: {len(strategies)}")

        if strategies:
            tokens = [f"{s._exchange}|{s._token}" for s in strategies]
            symbol_map = {
                s._tradingsymbol: f"{s._exchange}|{s._token}" for s in strategies
            }
            if is_backtest:
                strat = strategies[0]
                token = strat._token
                if not token:
                    logger.info(f"Resolving token for {strat._tradingsymbol} via broker-ai...")
                    sym = FinvasiaSymbol(exchange=strat._exchange, symbol=strat._tradingsymbol)
                    token = sym.find("token")

                if token:
                    def batch_fetch_history(exch: str, tkn: str, fm: str, to: str, tf: int) -> Any:
                        start = pdlm.from_format(fm, "YYYY-MM-DD")
                        end = pdlm.from_format(to, "YYYY-MM-DD")
                        all_data: list = []
                        current = end
                        while current > start:
                            batch_start = max(current.subtract(months=1), start)
                            data = broker_session.historical(
                                exch, tkn,
                                batch_start.int_timestamp,
                                current.int_timestamp,
                                tf,
                            )
                            if data is not None:
                                all_data.extend(data)
                            current = batch_start
                        if not all_data:
                            return None
                        seen: set = set()
                        deduped: list = []
                        for d in all_data:
                            t = d.get("time", "")
                            if t not in seen:
                                seen.add(t)
                                deduped.append(d)
                        return [{
                            "time": d.get("time", ""),
                            "open": float(d.get("into", 0)),
                            "high": float(d.get("inth", 0)),
                            "low": float(d.get("intl", 0)),
                            "close": float(d.get("intc", 0)),
                        } for d in deduped]

                    config = HistoricQuotesConfig(
                        symbol=str(token),
                        exchange=strat._exchange,
                        tradingsymbol=strat._tradingsymbol,
                        timeframe="5Min",
                        start_date=pdlm.now().subtract(days=365).date(),
                        end_date=pdlm.now().date(),
                    )
                    stream = HistoricQuotesHandler(config=config, fetch_history=batch_fetch_history)
                    stream.start()
                    logger.info(f"Backtest mode: loaded {len(stream.candles)} candles for {strat._tradingsymbol}")
                else:
                    logger.error(f"Could not resolve token for {strat._tradingsymbol}")
                    stream = None
            else:
                stream = StreamQuotesHandler(
                    broker_session=broker_session,
                    tokens=tokens,
                    symbol_map=symbol_map,
                )
                stream.start()
                quotes = stream.wait_for_quotes(
                    [s._tradingsymbol for s in strategies], timeout=15.0
                )
                logger.info(f"Initial quotes: {quotes}")
        else:
            stream = None

        backtest_tick = 0
        while True:
            try:
                if stream:
                    quotes = stream.get_quotes([s._tradingsymbol for s in strategies])
                else:
                    quotes = {}

                if is_backtest and stream:
                    candle_ratio = settings["global"]["candle"] // 5
                    candle_idx = backtest_tick // candle_ratio
                    for s in strategies:
                        s._candle.force_index(candle_idx)
                    backtest_tick += 1
                    if backtest_tick >= len(stream.candles):
                        logger.info(f"Backtest complete: {len(stream.candles)} candles processed")
                        break

                logger.info(
                    f"Tick: {len(quotes)} quotes, {len(strategies)} strategies active"
                )

                for strategy in strategies:
                    signal = runner.execute_tick(strategy=strategy, quotes=quotes)
                    if signal is not None:
                        logger.info(
                            f"Signal: {signal['action']} {signal['tradingsymbol']} @ {signal['price']}"
                        )
                        route_signal(
                            order_mgr,
                            signal,
                            broker_session,
                            holdings_tracker,
                            trades_journal,
                        )

                if not is_backtest:
                    time.sleep(1)

            except KeyboardInterrupt:
                logger.info("Shutdown requested")
                if stream:
                    stream.close()
                break

        logger.info("=== FTI Holdings: Done ===")

    except Exception as e:
        logger.error(f"Fatal: {e}")
        print_exc()


if __name__ == "__main__":
    main()
