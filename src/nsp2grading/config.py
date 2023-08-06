from pathlib import Path

from pydantic import BaseModel


class Config(BaseModel):
    root_path: Path = Path.home() / "tmp" / "grading_tool"
    submissions_path: Path = Path("submissions")
    code_path: Path = Path("code")
    env_prefix: str = "ECPC_"
