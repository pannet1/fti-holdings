from pydantic import BaseModel
from typing import Optional


class LoadSymbolsSchema(BaseModel):
    factory_dir: str
    symbols_file: Optional[str] = "symbols.yml"
