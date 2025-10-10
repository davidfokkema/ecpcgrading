try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from pathlib import Path

from pydantic import BaseModel


class EnvironmentConfig(BaseModel):
    name: str
    python_version: str = "3.12"
    package_spec: str = ""


class Config(BaseModel):
    root_path: Path
    submissions_path: Path = Path("submissions")
    code_path: Path = Path("code")
    env_prefix: str = "ECPC_"
    course_alias: str
    assignment_group: str
    groupset: str | None = None
    group: str | None = None
    env: dict[str, EnvironmentConfig]
    theme: str = "textual-dark"


def read_config(folder: Path):
    defaults = {"root_path": folder}
    with open(folder / "grading.toml", "rb") as f:
        data = tomllib.load(f)
    return Config.model_validate(defaults | data)
