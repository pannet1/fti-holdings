import logging
from pathlib import Path
from typing import Optional

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
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        app_key_hash: Optional[str] = None,
    ) -> dict:
        if not userid or not password or not totp_secret:
            raise ValueError(
                "Missing required credentials. "
                "Check apps/backend/data/auth.yaml has userid, password, and totp_secret."
            )

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
            access_token=None,
            refresh_token=None,
            app_key_hash=app_key_hash,
        )

        result = fin.authenticate()
        if not result:
            raise RuntimeError(f"Authentication failed for {userid}")

        token_file = Path(token_path)
        token_file.parent.mkdir(parents=True, exist_ok=True)
        with open(token_file, "w") as f:
            f.write(result.get("access_token", ""))
        logger.info(f"Authentication successful for {userid}")

        return {"status": "authenticated", "userid": userid, "session": fin}
