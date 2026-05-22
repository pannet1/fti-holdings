from pydantic import BaseModel
from typing import Optional


class BrokerAuthenticateSchema(BaseModel):
    userid: str
    password: str
    totp_secret: str
    api_key: str
    api_secret: str
    imei: str
    oauth_url: str
    token_path: str
    vendor_code: Optional[str] = ""
