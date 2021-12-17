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
    cwd = Path.cwd()
    for directory in [cwd] + list(cwd.parents):
        if (directory / CONFIG_FILE).exists():
            print(f"Configuration file found. Doing nothing.")
            break
    else:
        print("Creating default config file...")
        default_config = importlib.resources.read_text(*DEFAULT_CONFIG)
        Path(CONFIG_FILE).write_text(default_config)


if __name__ == "__main__":
    cli()
