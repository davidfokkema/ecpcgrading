import importlib.resources
import re
import zipfile
from pathlib import Path

import click
import tomlkit
from rich import print
from rich.progress import track

CONFIG_FILE = "grading.toml"
DEFAULT_CONFIG = "nsp2grading", "default_config.toml"

RE_STUDENT_NAME = "(?P<name>[a-z]+)_"


@click.group()
def cli():
    """Grading tool for NSP2 data acquisition course."""
    print()


@cli.command()
def init():
    """Initialize configuration file for grading."""
    config_path = find_config_file()
    if config_path is not None:
        print(f"Configuration file found. Doing nothing.")
    else:
        print("Creating default config file...")
        default_config = importlib.resources.read_text(*DEFAULT_CONFIG)
        Path(CONFIG_FILE).write_text(default_config)


@cli.command("unpack")
def uncompress_submissions():
    """Uncompress student submissions."""
    config = read_config()
    if config is None:
        print("[red bold]Error: no configuration file found.")
    else:
        grading_home = find_config_file().parent
        code_dir = grading_home / config["general"]["code_dir"]
        code_dir.mkdir(exist_ok=True)
        submissions_dir = grading_home / config["general"]["submissions_dir"]

        submissions = submissions_dir.glob("*.zip")
        for submission in track(
            list(submissions), description="Unpacking submissions..."
        ):
            student = re.match(RE_STUDENT_NAME, submission.name).group("name")
            student_dir = code_dir / student
            if not student_dir.is_dir():
                student_dir.mkdir()
                zip_file = zipfile.ZipFile(submission)
                zip_file.extractall(path=student_dir)
                print(f"[blue]Processed {student}.")


def find_config_file():
    """Search current working directory and its parents for config file."""
    cwd = Path.cwd()
    for directory in [cwd] + list(cwd.parents):
        config_path = directory / CONFIG_FILE
        if config_path.exists():
            return config_path
    return None


def read_config():
    """Read configuration file."""
    config_path = find_config_file()
    if config_path is None:
        return None
    else:
        return tomlkit.parse(config_path.read_text())


if __name__ == "__main__":
    cli()
