import logging
from pathlib import Path
from traceback import print_exc

import yaml

from app.features.broker.AuthenticateBroker.Handler import AuthenticateBrokerHandler

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
AUTH_FILE = DATA_DIR / "auth.yaml"


def main():
    try:
        with open(AUTH_FILE) as f:
            creds = yaml.safe_load(f)["finvasia"]

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
        )
        logger.info(f"Authenticated: {auth['status']}")

        broker_session = auth["session"].broker

        for exchange, symbol in [("BSE", "ITBEES"), ("BSE", "MOTHERSON")]:
            logger.info(f"Subscribing to {exchange}|{symbol}")
            result = broker_session.searchscrip(exchange, symbol)
            if result:
                token = result["values"][0]["token"]
                logger.info(f"Token for {symbol}: {token}")
                broker_session.subscribe([token])
                logger.info(f"Subscribed to {symbol} via WebSocket")
            else:
                logger.error(f"Failed to resolve {exchange}|{symbol}")

        broker_session.start_websocket()
        logger.info("WebSocket started. Quotes arriving via last_price dict.")

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        print_exc()


if __name__ == "__main__":
    main()
