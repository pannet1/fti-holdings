import pytest
from pathlib import Path

from .Handler import BrokerAuthenticateHandler

DUMMY_CREDS = dict(
    api_key="api_key",
    api_secret="api_secret",
    imei="abc1234",
    oauth_url="https://example.com/auth",
)


class TestBrokerAuthenticateHandler:

    def test_reuses_existing_token(self, tmp_path):
        handler = BrokerAuthenticateHandler()
        token_file = tmp_path / "FN137030.txt"
        token_file.write_text("session_token_abc")
        result = handler.execute(
            userid="FN137030",
            password="pass",
            totp_secret="secret",
            token_path=str(token_file),
            **DUMMY_CREDS,
        )
        assert result["status"] == "token_exists"
        assert result["userid"] == "FN137030"

    def test_raises_on_empty_credentials(self):
        handler = BrokerAuthenticateHandler()
        with pytest.raises(ValueError, match="Missing required credentials"):
            handler.execute(
                userid="",
                password="",
                totp_secret="",
                token_path="/tmp/nonexistent/FN137030.txt",
                **DUMMY_CREDS,
            )

    def test_raises_on_missing_password(self):
        handler = BrokerAuthenticateHandler()
        with pytest.raises(ValueError, match="Missing required credentials"):
            handler.execute(
                userid="FN137030",
                password="",
                totp_secret="secret",
                token_path="/tmp/nonexistent/FN137030.txt",
                **DUMMY_CREDS,
            )
