from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from zipfile import ZipFile

import requests
from canvas_course_tools.datatypes import Assignment as CanvasAssignment
from canvas_course_tools.datatypes import CanvasAttachment
from canvas_course_tools.datatypes import Student as CanvasStudent
from slugify import slugify
from textual import on, work
from textual.app import ComposeResult, log
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.events import Key
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    Collapsible,
    Footer,
    Header,
    Label,
    ListItem,
    ListView,
    LoadingIndicator,
    Log,
    Static,
)
from textual.worker import Worker, WorkerFailed, WorkerState

from ecpcgrading.config import Config, EnvironmentConfig

if TYPE_CHECKING:
    from ecpcgrading.assignments import Assignment
    from ecpcgrading.students import Student
    from ecpcgrading.tui import GradingTool


@dataclass
class TaskError(Exception):
    msg: str
    details: str


class Task(ListItem):
    run_msg: str = "Running task..."
    success_msg: str = "Finished task"
    error_msg: str = "Task failed"

    app: GradingTool

    def __init__(self, title: str = "", *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.title = title

    def compose(self) -> ComposeResult:
        yield Label(self.title)

    def execute(self, assignment: Assignment, student: Student) -> Worker:
        self._assignment = assignment._assignment
        self._student = student._student
        self.app.push_screen(RunTaskModal(self.run_msg))
        # run worker and return worker to caller
        return self.run_task()

    @work(thread=True)
    def run_task(self) -> None: ...

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.RUNNING:
            log(self.run_msg)
        elif event.state == WorkerState.SUCCESS:
            log(self.success_msg)
            self.app.pop_screen()
        elif event.state == WorkerState.ERROR:
            log(self.error_msg)
            self.app.pop_screen()
            self.app.push_screen(
                TaskErrorModal(self.error_msg, exception=event.worker.error)
            )


class RunTaskModal(ModalScreen):
    def __init__(
        self,
        msg: str,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)
        self.msg = msg

    def compose(self) -> ComposeResult:
        with Vertical(id="modal_dialog"):
            with Center():
                yield Label(self.msg)
            yield LoadingIndicator()


class TaskErrorModal(ModalScreen):
    def __init__(
        self,
        msg: str,
        exception: TaskError,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)
        self.msg = msg
        self.exception = exception

    def compose(self) -> ComposeResult:
        with Vertical(id="modal_dialog"):
            yield Label(f"{self.msg}: {self.exception}", id="error_msg")
            with Collapsible(title="Detailed output"):
                yield Log()
            with Center():
                yield Button("Close", variant="primary")

    def on_mount(self) -> None:
        try:
            self.query_one(Log).write(self.exception.details)
        except AttributeError:
            self.query_one(Collapsible).remove()
            self.query_one("#modal_dialog").styles.height = "auto"
        self.query_one(Button).focus()

    @on(Button.Pressed)
    def close_dialog(self, event: Button.Pressed) -> None:
        self.dismiss()


class DownloadTask(Task):
    run_msg = "Downloading submission..."
    success_msg = "Download successful"
    error_msg = "Download failed"

    @work(thread=True, exit_on_error=False)
    def run_task(self):
        student_name = slugify(self._student.name)
        submissions_dir = get_submissions_dir(self.app.config, self._assignment)

        submission = self.app.canvas_tasks.get_submissions(
            self._assignment, self._student
        )
        if submission.attempt is None:
            raise RuntimeError("Student did not yet submit this assignment")

        Path.mkdir(submissions_dir, parents=True, exist_ok=True)
        match submission.attachments:
            case [CanvasAttachment() as attachment]:
                submission_path = (
                    submissions_dir / f"{student_name}_{attachment.filename}"
                )
                file_type = submission_path.suffix
                file_contents = requests.get(attachment.url).content
                submission_path.write_bytes(file_contents)
                self.app.call_from_thread(
                    self.notify, f"Downloaded a single {file_type}-file"
                )
            case [*attachments]:
                self.zip_attachments(student_name, submissions_dir, attachments)
                self.app.call_from_thread(
                    self.notify,
                    f"Zipped {len(attachments)} submitted file(s)",
                    severity="warning",
                )

    def zip_attachments(
        self, student_name, submissions_dir, attachments: list[CanvasAttachment]
    ):
        submission_path = submissions_dir / (student_name + "_zipped.zip")
        with ZipFile(submission_path, mode="w") as f:
            for attachment in attachments:
                file_contents = requests.get(attachment.url).content
                f.writestr(attachment.filename, data=file_contents)


class DecompressCodeTask(Task):
    run_msg = "Extracting files..."
    success_msg = "Code successfully decompressed"
    error_msg = "Decompression failed"

    @work(thread=True, exit_on_error=False)
    def run_task(self):
        submissions_dir = get_submissions_dir(self.app.config, self._assignment)
        code_dir = get_code_dir(self.app.config, self._assignment, self._student)
        student_name = slugify(self._student.name)

        match list(submissions_dir.glob(f"{student_name}_*")):
            case [path]:
                if code_dir.exists():
                    self.app.call_from_thread(
                        self.notify,
                        f"Removing existing directory {code_dir}",
                        severity="warning",
                    )
                    shutil.rmtree(code_dir, onerror=remove_readonly)
                Path.mkdir(code_dir, parents=True)
                match path.suffix:
                    case ".zip":
                        with ZipFile(path) as f:
                            f.extractall(path=code_dir)
                        self.app.call_from_thread(
                            self.notify, "Extracted submitted files"
                        )
                    case ".bundle":
                        process = subprocess.run(
                            ["git", "clone", "-b", "main", path, code_dir],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                        )
                        self.log(process.stdout.decode())
                        if process.returncode:
                            raise TaskError(
                                f"Process exited with exit code: {process.returncode}",
                                details=process.stdout.decode(),
                            )
                        self.app.call_from_thread(
                            self.notify, "Cloned submitted repository"
                        )
                    case _:
                        # default case, .py or something else
                        # copy it as-is to the code directory
                        target_name = path.name.removeprefix(f"{student_name}_")
                        shutil.copy(path, code_dir / target_name)
                        self.app.call_from_thread(self.notify, f"Copied {target_name}")
            case [_, *_]:
                raise RuntimeError("More than one submission file")
            case _:
                raise RuntimeError("Can't locate submission file")


class CreateEnvTask(Task):
    success_msg = "Environment successfully created"
    error_msg = "Environment creation failed"

    def __init__(self, title: str, env: EnvironmentConfig, *args, **kwargs) -> None:
        super().__init__(title, *args, **kwargs)
        self.run_msg = f"Creating environment ({env.name})..."
        self.env = env

    @work(thread=True, exit_on_error=False)
    def run_task(self):
        command = f"uv venv --python {self.env.python_version}"
        if self.env.package_spec:
            command += (
                f" && uv pip install --python .venv/bin/python {self.env.package_spec}"
            )
        process = subprocess.run(
            command,
            cwd=get_code_dir(
                self.app.config, self._assignment, self._student, check_subdir=True
            ),
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        output = process.stdout.decode()
        self.log(output)
        if process.returncode:
            raise TaskError(
                f"Process exited with exit code: {process.returncode}", details=output
            )
        self.app.call_from_thread(self.notify, "Created clean environment")


class OpenCodeTask(Task):
    run_msg = "Starting Visual Studio Code..."
    success_msg = "Visual Studio Code is running"
    error_msg = "Could not start Visual Studio Code"

    @work(thread=True, exit_on_error=False)
    def run_task(self):
        code_dir = get_code_dir(
            self.app.config, self._assignment, self._student, check_subdir=True
        )
        if not code_dir.exists():
            raise RuntimeError("Please download and extract submission first.")

        (settings_dir := code_dir / ".vscode").mkdir(parents=True, exist_ok=True)
        (settings_dir / "settings.json").write_text(
            json.dumps({"python.defaultInterpreterPath": ".venv/bin/python"})
        )
        (settings_dir / ".gitignore").write_text("*")

        # start VS Code
        process = subprocess.run(
            f'code "{code_dir}"',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.log(process.stdout.decode())
        if process.returncode:
            raise RuntimeError(f"Process exited with exit code: {process.returncode}")


def get_submissions_dir(config: Config, assignment: CanvasAssignment):
    return config.root_path / slugify(assignment.name) / config.submissions_path


def get_code_dir(
    config: Config,
    assignment: CanvasAssignment,
    student: CanvasStudent,
    check_subdir: bool = False,
) -> Path:
    student_dir = (
        config.root_path
        / slugify(assignment.name)
        / config.code_path
        / slugify(student.name)
    )

    if check_subdir and student_dir.exists():
        dir_contents: Path = list(student_dir.iterdir())
        if len(dir_contents) == 1 and dir_contents[0].is_dir():
            # student submitted a directory containing all the files, use that
            # directory as code dir
            return dir_contents[0]
    return student_dir


def remove_readonly(func, path, excinfo):
    """Make a path writable and retry the failed function call."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


class Tasks(ListView):
    app: "GradingTool"

    def __init__(self, assignment: Assignment, student: Student) -> None:
        super().__init__()
        self.assignment = assignment
        self.student = student

    def compose(self) -> ComposeResult:
        yield DownloadTask("Download Submission [dim]\[d]", id="download_task")
        yield DecompressCodeTask(
            "Extract submission into grading folder [dim]\[e]", id="extract_task"
        )
        for idx, env in enumerate(self.app.config.env.values()):
            yield CreateEnvTask(
                f"Create virtual environment: {env.name} [dim]\[{idx}]",
                env=env,
                id=f"create_env{idx}_task",
            )
        yield OpenCodeTask("Open Visual Studio Code [dim]\[o]", id="open_vscode_task")

    @on(ListView.Selected)
    def execute_task(self, selected: ListView.Selected) -> None:
        selected.item.execute(self.assignment, self.student)


class TasksScreen(Screen):
    BINDINGS = [
        ("escape", "go_back", "Back to Students"),
        Binding("d", "download", show=False),
        Binding("e", "extract_submission", show=False),
        Binding("o", "open_vscode", show=False),
        ("s", "speedrun", "Speedrun"),
    ]

    def __init__(self, assignment: Assignment, student: Student) -> None:
        super().__init__()
        self.assignment = assignment
        self.student = student

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Horizontal(
            Button("< Students", id="back"),
            Static("", id="spacer"),
            Label(self.assignment.title),
            Label(f"({self.student.student_name})"),
            id="breadcrumbs",
        )
        yield Label("Please Select a Task", id="list_header")
        yield Tasks(self.assignment, self.student)

    def on_mount(self) -> None:
        self.query_one("Tasks").focus()

    @on(Button.Pressed, "#back")
    def action_go_back(self) -> None:
        self.dismiss()

    def run_task(self, task_id) -> None:
        self.query_one(task_id, Task).execute(self.assignment, self.student)

    async def run_task_wait(self, task_id) -> None:
        # WIP: Nice idea, but blocking the event queue results in behavior that
        # depends on whether it is blocked in the action, or the on_key method.
        # Sometimes the keys are queued for this screen, sometimes they are
        # dumped on the modal, it all depends. And when an error occurs the keys
        # can get dumped in that new error dialog. So this is not very useful
        # for quickly typing several shortcuts and have that result in a queue
        # of tasks to perform. Leaving this for now.
        worker = self.query_one(task_id, Task).execute(self.assignment, self.student)
        try:
            await worker.wait()
        except WorkerFailed:
            # any error is handled by the task
            pass
        return worker

    def on_key(self, event: Key) -> None:
        try:
            # was key 0-9 pressed?
            idx = int(event.key)
        except ValueError:
            pass
        else:
            if idx < len(self.app.config.env):
                # check idx bound for number of environment entries
                self.run_task(f"#create_env{idx}_task")

    async def action_download(self) -> None:
        await self.run_task_wait("#download_task")

    async def action_extract_submission(self) -> None:
        await self.run_task_wait("#extract_task")

    async def action_open_vscode(self) -> None:
        await self.run_task_wait("#open_vscode_task")

    async def action_speedrun(self) -> None:
        for task_id in [
            "#download_task",
            "#extract_task",
            "#create_env0_task",
            "#open_vscode_task",
        ]:
            worker = await self.run_task_wait(task_id)
            if worker.error:
                # there was an error, abort speedrun
                break
