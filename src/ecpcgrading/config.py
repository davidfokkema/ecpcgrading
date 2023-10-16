import tomllib
from pathlib import Path

from pydantic import BaseModel


class Config(BaseModel):
    root_path: Path
    submissions_path: Path = Path("submissions")
    code_path: Path = Path("code")
    env_prefix: str = "ECPC_"
    server: str
    course_id: int
    assignment_group: str
    groupset: str
    group: str


def read_config(folder: Path):
    defaults = {"root_path": folder}
    with open(folder / "grading.toml", "rb") as f:
        data = tomllib.load(f)
    return Config.model_validate(defaults | data)
