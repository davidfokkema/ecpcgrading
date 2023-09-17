from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import TYPE_CHECKING
from zipfile import ZipFile

from slugify import slugify
from textual import on, work
from textual.app import ComposeResult, log
from textual.containers import Center, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ListItem, LoadingIndicator
from textual.worker import Worker, WorkerState

if TYPE_CHECKING:
    from nsp2grading.tui import Assignment, GradingTool, Student


class Task(ListItem):
    run_msg: str = "Running task..."
    success_msg: str = "Finished task"
    error_msg: str = "Task failed"

    app: GradingTool

    def __init__(self, title: str) -> None:
        super().__init__()
        self.title = title

    def compose(self) -> ComposeResult:
        yield Label(self.title)

    def execute(self, assignment: Assignment, student: Student) -> None:
        self._assignment = assignment
        self._student = student
        self.app.push_screen(RunTaskModal(self.run_msg))
        self.run_task()

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
        # FIXME: this is placeholder code to grab a file from the filesystem instead of a canvas download
        config = self.app.config
        assignment = slugify(self._assignment.title)
        submissions_dir = config.root_path / assignment / config.submissions_path
        submission_path = submissions_dir / (
            slugify(self._student.student_name) + "_pythondaq.zip"
        )
        Path.mkdir(submissions_dir, parents=True, exist_ok=True)
        shutil.copy(Path.home() / "tmp" / "test_coursedaq.zip", submission_path)
        time.sleep(1)


class UncompressCodeTask(Task):
    run_msg = "Extracting files..."
    success_msg = "Code successfully decompressed"
    error_msg = "Decompression failed"

    @work(thread=True, exit_on_error=False)
    def run_task(self):
        config = self.app.config
        assignment = slugify(self._assignment.title)
        submissions_dir = config.root_path / assignment / config.submissions_path
        student_name = slugify(self._student.student_name)
        code_dir = config.root_path / assignment / config.code_path / student_name

        match list(submissions_dir.glob(student_name + "_*.zip")):
            case [path]:
                if code_dir.exists():
                    self.log(f"Removing existing directory {code_dir}")
                    shutil.rmtree(code_dir)
                Path.mkdir(code_dir, parents=True)
                with ZipFile(path) as f:
                    f.extractall(path=code_dir)
            case [_, *_]:
                raise RuntimeError("More than one submission file")
            case _:
                raise RuntimeError("Can't locate submission file")


class CreateEnvTask(Task):
    ...


class OpenCodeTask(Task):
    ...
