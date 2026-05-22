from pydantic import BaseModel
from typing import Optional


class SymbolsLoadSchema(BaseModel):
    factory_dir: str
    symbols_file: Optional[str] = "symbols.yml"
