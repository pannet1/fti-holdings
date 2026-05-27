import logging
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class AuthenticateBrokerHandler:

    def _try_auth(self, fin: object, retries: int = 3, delay: int = 2) -> Optional[dict]:
        for attempt in range(1, retries + 1):
            try:
                result = fin.authenticate()
                if result:
                    return result
                logger.warning(f"Auth returned empty result (attempt {attempt}/{retries})")
            except Exception as e:
                logger.error(f"Auth attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                time.sleep(delay)
        return None

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

        token_file = Path(token_path)
        if token_file.exists():
            content = token_file.read_text().strip()
            if content:
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
                    access_token=content,
                    refresh_token=refresh_token,
                    app_key_hash=app_key_hash,
                )
                result = self._try_auth(fin)
                if result:
                    logger.info(f"Token reuse successful for {userid}")
                    return {"status": "token_exists", "userid": userid, "session": fin}
                logger.warning(f"Token reuse failed, deleting stale token for {userid}")
                token_file.unlink(missing_ok=True)

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

        result = self._try_auth(fin)
        if not result:
            raise RuntimeError(f"Authentication failed for {userid} after retries")

        token_file.parent.mkdir(parents=True, exist_ok=True)
        with open(token_file, "w") as f:
            f.write(result.get("access_token", ""))
        logger.info(f"Authentication successful for {userid}")

        return {"status": "authenticated", "userid": userid, "session": fin}
