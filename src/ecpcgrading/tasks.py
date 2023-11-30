from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from zipfile import ZipFile

import requests
from canvas_course_tools.datatypes import Assignment as CanvasAssignment
from canvas_course_tools.datatypes import Attachment
from canvas_course_tools.datatypes import Student as CanvasStudent
from slugify import slugify
from textual import on, work
from textual.app import ComposeResult, log
from textual.containers import Center, Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Label,
    ListItem,
    ListView,
    LoadingIndicator,
    Static,
)
from textual.worker import Worker, WorkerState

from ecpcgrading.config import Config, EnvironmentConfig

if TYPE_CHECKING:
    from ecpcgrading.assignments import Assignment
    from ecpcgrading.students import Student
    from ecpcgrading.tui import GradingTool


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
    def run_task(self) -> None:
        ...

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
        exception: Exception,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)
        self.msg = msg
        self.exception = exception

    def compose(self) -> ComposeResult:
        with Vertical(id="modal_dialog"):
            with Center():
                yield Label(f"{self.msg}: {self.exception}", id="error_msg")
            with Center():
                yield Button("Close", variant="primary")

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

        submission = self.app.canvas_tasks.get_submission(
            self._assignment, self._student
        )
        if submission.attempt is None:
            raise RuntimeError(f"Student did not yet submit this assignment")

        Path.mkdir(submissions_dir, parents=True, exist_ok=True)
        match submission.attachments:
            case [
                Attachment(content_type="application/x-zip-compressed") as attachment
            ]:
                submission_path = submissions_dir / (
                    student_name + "_" + attachment.name
                )
                file_contents = requests.get(attachment.url).content
                submission_path.write_bytes(file_contents)
                self.app.call_from_thread(self.notify, f"Downloaded a single zipfile")
            case [*attachments]:
                self.zip_attachments(student_name, submissions_dir, attachments)
                self.app.call_from_thread(
                    self.notify,
                    f"Zipped {len(attachments)} submitted file(s)",
                    severity="warning",
                )

    def zip_attachments(self, student_name, submissions_dir, attachments):
        submission_path = submissions_dir / (student_name + "_zipped.zip")
        with ZipFile(submission_path, mode="w") as f:
            for attachment in attachments:
                file_contents = requests.get(attachment.url).content
                f.writestr(attachment.name, data=file_contents)


class UncompressCodeTask(Task):
    run_msg = "Extracting files..."
    success_msg = "Code successfully decompressed"
    error_msg = "Decompression failed"

    @work(thread=True, exit_on_error=False)
    def run_task(self):
        submissions_dir = get_submissions_dir(self.app.config, self._assignment)
        code_dir = get_code_dir(self.app.config, self._assignment, self._student)
        student_name = slugify(self._student.name)

        match list(submissions_dir.glob(student_name + "_*.zip")):
            case [path]:
                if code_dir.exists():
                    self.app.call_from_thread(
                        self.notify,
                        f"Removing existing directory {code_dir}",
                        severity="warning",
                    )
                    shutil.rmtree(code_dir)
                Path.mkdir(code_dir, parents=True)
                with ZipFile(path) as f:
                    f.extractall(path=code_dir)
                self.app.call_from_thread(self.notify, "Extracted submitted files")
            case [_, *_]:
                raise RuntimeError("More than one submission file")
            case _:
                raise RuntimeError("Can't locate submission file")


class CreateEnvTask(Task):
    run_msg = "Creating Conda environment..."
    success_msg = "Conda environment successfully created"
    error_msg = "Environment creation failed"

    def __init__(self, title: str, env: EnvironmentConfig, *args, **kwargs) -> None:
        super().__init__(title, *args, **kwargs)
        self.env = env

    @work(thread=True, exit_on_error=False)
    def run_task(self):
        env_name = "ECPC_" + slugify(self._student.name)
        process = subprocess.run(
            f"conda create -n {env_name} -c {self.env.channel} {self.env.package_spec} --yes",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.log(process.stdout.decode())
        if process.returncode:
            raise RuntimeError(f"Process exited with exit code: {process.returncode}")
        self.app.call_from_thread(self.notify, "Created clean conda environment")


class OpenCodeTask(Task):
    run_msg = "Starting Visual Studio Code..."
    success_msg = "Visual Studio Code is running"
    error_msg = "Could not start Visual Studio Code"

    @work(thread=True, exit_on_error=False)
    def run_task(self):
        config = self.app.config
        assignment = slugify(self._assignment.name)
        student_name = slugify(self._student.name)
        env_name = "ECPC_" + slugify(self._student.name)
        code_dir = config.root_path / assignment / config.code_path / student_name

        dir_contents: Path = list(code_dir.iterdir())
        if len(dir_contents) == 1 and dir_contents[0].is_dir():
            code_dir = dir_contents[0]

        process = subprocess.run(
            f'conda run -n {env_name} code "{code_dir}"',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.log(process.stdout.decode())
        if process.returncode:
            raise RuntimeError(f"Process exited with exit code: {process.returncode}")


def get_submissions_dir(config: Config, assignment: CanvasAssignment):
    return config.root_path / slugify(assignment.name) / config.submissions_path


def get_code_dir(config: Config, assignment: CanvasAssignment, student: CanvasStudent):
    return (
        config.root_path
        / slugify(assignment.name)
        / config.code_path
        / slugify(student.name)
    )


class Tasks(ListView):
    app: "GradingTool"

    def __init__(self, assignment: Assignment, student: Student) -> None:
        super().__init__()
        self.assignment = assignment
        self.student = student

    def compose(self) -> ComposeResult:
        yield DownloadTask("Download Submission", id="download_task")
        yield UncompressCodeTask(
            "Extract submission into grading folder", id="extract_task"
        )
        for idx, env in enumerate(self.app.config.env.values()):
            yield CreateEnvTask(
                f"Create conda environment: {env.name}",
                env=env,
                id=f"create_env{idx}_task",
            )
        yield OpenCodeTask("Open Visual Studio Code")

    @on(ListView.Selected)
    def execute_task(self, selected: ListView.Selected) -> None:
        selected.item.execute(self.assignment, self.student)


class TasksScreen(Screen):
    BINDINGS = [("b", "go_back", "Back to Students"), ("s", "speedrun", "Speedrun")]

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

    async def action_speedrun(self):
        for task_id in ["#download_task", "#extract_task", "#create_env0_task"]:
            task: Task = self.query_one(task_id)
            worker = task.execute(self.assignment, self.student)
            await worker.wait()
