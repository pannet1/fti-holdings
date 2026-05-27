import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from .Handler import AuthenticateBrokerHandler

DUMMY_CREDS = dict(
    api_key="api_key",
    api_secret="api_secret",
    imei="abc1234",
    oauth_url="https://example.com/auth",
)


class TestAuthenticateBrokerHandler:

    @patch("broker_ai.finvasia.finvasia.Finvasia")
    def test_reuses_existing_token(self, mock_finvasia, tmp_path):
        mock_instance = MagicMock()
        mock_instance.authenticate.return_value = {
            "access_token": "session_token_abc",
            "user_id": "FN137030",
        }
        mock_finvasia.return_value = mock_instance
        handler = AuthenticateBrokerHandler()
        token_file = tmp_path / "FN137030.txt"
        token_file.write_text("session_token_abc")
        result = handler.execute(
            userid="FN137030",
            password="pass",
            totp_secret="secret",
            token_path=str(token_file),
            **DUMMY_CREDS,
        )
        assert result["status"] == "authenticated"
        assert result["userid"] == "FN137030"

    def test_raises_on_empty_credentials(self):
        handler = AuthenticateBrokerHandler()
        with pytest.raises(ValueError, match="Missing required credentials"):
            handler.execute(
                userid="",
                password="",
                totp_secret="",
                token_path="/tmp/nonexistent/FN137030.txt",
                **DUMMY_CREDS,
            )

    def test_raises_on_missing_password(self):
        handler = AuthenticateBrokerHandler()
        with pytest.raises(ValueError, match="Missing required credentials"):
            handler.execute(
                userid="FN137030",
                password="",
                totp_secret="secret",
                token_path="/tmp/nonexistent/FN137030.txt",
                **DUMMY_CREDS,
            )
