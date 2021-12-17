import importlib.resources
from pathlib import Path

import click

CONFIG_FILE = "grading.toml"
DEFAULT_CONFIG = "nsp2grading", "default_config.toml"


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


def find_config_file():
    """Search current working directory and its parents for config file."""
    cwd = Path.cwd()
    for directory in [cwd] + list(cwd.parents):
        config_path = directory / CONFIG_FILE
        if config_path.exists():
            return config_path
    return None


if __name__ == "__main__":
    cli()
