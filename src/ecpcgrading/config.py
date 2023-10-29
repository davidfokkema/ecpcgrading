try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from pathlib import Path

from pydantic import BaseModel


class EnvironmentConfig(BaseModel):
    name: str
    channel: str = "defaults"
    package_spec: str = "python"


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


def read_config(folder: Path):
    defaults = {"root_path": folder}
    with open(folder / "grading.toml", "rb") as f:
        data = tomllib.load(f)
    return Config.model_validate(defaults | data)
