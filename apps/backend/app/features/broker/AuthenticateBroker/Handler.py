import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class AuthenticateBrokerHandler:

    def execute(
        self,
        userid: str,
        password: str,
        totp_secret: str,
        api_key: str,
        api_secret: str,
        imei: str,
        oauth_url: str,
        token_path: str,
        vendor_code: str = "",
    ) -> dict:
        if not userid or not password or not totp_secret:
            raise ValueError(
                "Missing required credentials. "
                "Check apps/backend/data/auth.yaml has userid, password, and totp_secret."
            )

        token_file = Path(token_path)
        if token_file.exists():
            logger.info(f"Session token found at {token_path}, attempting reuse")
            return {"status": "token_exists", "userid": userid, "token_path": token_path}

        from broker_ai.finvasia.finvasia import Finvasia
        fin = Finvasia(
            user_id=userid,
            password=password,
            pin=totp_secret,
            vendor_code=vendor_code,
            app_key=api_key,
            api_secret=api_secret,
            imei=imei,
            oauth_url=oauth_url,
        )

        fin.authenticate()

        token_file.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Authentication successful for {userid}")

        return {"status": "authenticated", "userid": userid, "session": fin}
