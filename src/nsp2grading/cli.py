import importlib.resources
import re
import subprocess
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
@click.pass_context
def cli(ctx):
    """Grading tool for NSP2 data acquisition course."""
    print()
    config_path = find_config_file()
    if ctx.invoked_subcommand != "init":
        if config_path is None:
            print(
                "[bold red]Configuration file not found. First invoke the 'init' command."
            )
            raise click.Abort()
        else:
            config = read_config(config_path)
            ctx.ensure_object(dict)
            ctx.obj["config"] = config
            ctx.obj["grading_home"] = config_path.parent


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
@click.pass_context
def uncompress_submissions(ctx):
    """Uncompress student submissions."""
    config = ctx.obj["config"]
    grading_home = ctx.obj["grading_home"]
    code_dir = grading_home / config["general"]["code_dir"]
    code_dir.mkdir(exist_ok=True)
    submissions_dir = grading_home / config["general"]["submissions_dir"]

    submissions = submissions_dir.glob("*.zip")
    for submission in track(list(submissions), description="Unpacking submissions..."):
        student = re.match(RE_STUDENT_NAME, submission.name).group("name")
        student_dir = code_dir / student
        if not student_dir.is_dir():
            student_dir.mkdir()
            zip_file = zipfile.ZipFile(submission)
            zip_file.extractall(path=student_dir)
            print(f"[blue]Processed {student}.")


@cli.group()
def env():
    """Manage conda environments for all students."""
    pass


@env.command("list")
def list_environments():
    """List all student conda environments."""
    pass


@env.command("create")
def create_environments():
    """Create conda environments for all students."""
    config = read_config()
    if config is None:
        print("[red bold]Error: no configuration file found.")
    else:
        grading_home = find_config_file().parent
        code_dir = grading_home / config["general"]["code_dir"]
        students = [p.name for p in code_dir.iterdir() if p.is_dir()]

        for student in track(students, description="Creating environments..."):
            env_name = f"env_{student}"
            print(f"[blue]Creating {env_name}...")
            subprocess.run(
                f"conda create -n {env_name} python=3.9 --yes",
                shell=True,
                capture_output=True,
            )


def find_config_file():
    """Search current working directory and its parents for config file."""
    cwd = Path.cwd()
    for directory in [cwd] + list(cwd.parents):
        config_path = directory / CONFIG_FILE
        if config_path.exists():
            return config_path
    return None


def read_config(config_path):
    """Read configuration file.

    Args:
        config_path (pathlib.Path): Location of the TOML configuration file.

    Returns:
        dict: a configuration object.
    """
    if config_path is None:
        return None
    else:
        return tomlkit.parse(config_path.read_text())


if __name__ == "__main__":
    cli()
