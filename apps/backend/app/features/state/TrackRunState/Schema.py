from pydantic import BaseModel
from typing import Optional


class TrackRunStateSchema(BaseModel):
    data_dir: str
    run_file: Optional[str] = "run.txt"
