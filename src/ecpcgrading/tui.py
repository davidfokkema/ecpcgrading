from pathlib import Path

from canvas_course_tools.canvas_tasks import CanvasTasks
from canvas_course_tools.datatypes import Assignment as CanvasAssignment
from canvas_course_tools.datatypes import Course as CanvasCourse
from canvas_course_tools.datatypes import Student as CanvasStudent
from canvas_course_tools.utils import find_course
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Center, Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, LoadingIndicator
from textual.worker import Worker, WorkerState

import ecpcgrading.config
from ecpcgrading import canvas
from ecpcgrading.assignments import AssignmentsScreen


class StartupScreen(ModalScreen):
    app: "GradingTool"

    def compose(self) -> ComposeResult:
        with Vertical(id="modal_dialog"):
            with Center():
                yield Label(id="msg")
            yield LoadingIndicator()

    def on_mount(self) -> None:
        self.query_one("#msg").update("Fetching assignments and students...")
        self.get_assignments_and_students()

    @work(thread=True)
    def get_assignments_and_students(self) -> list[str]:
        config: ecpcgrading.config.Config = self.app.config
        canvas_tasks, course = find_course(config.course_alias)
        assignments = canvas.get_assignments(
            canvas_tasks, course, config.assignment_group
        )
        students = canvas.get_students(
            canvas_tasks, course, config.groupset, config.group
        )
        self.app.canvas_tasks = canvas_tasks
        self.app.course = course
        return assignments, students

    @on(Worker.StateChanged)
    def return_assignments(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.SUCCESS:
            assignments, students = event.worker.result
            self.dismiss((assignments, students))


class GradingTool(App):
    TITLE = "Grading Tool for ECPC"
    CSS_PATH = "grading_tool.tcss"
    BINDINGS = [("q", "quit", "Quit")]

    config: ecpcgrading.config.Config
    canvas_tasks: CanvasTasks
    course: CanvasCourse
    assignments: list[CanvasAssignment]
    students: list[CanvasStudent]

    def __init__(self):
        super().__init__()
        try:
            self.config = ecpcgrading.config.read_config(Path.cwd())
        except FileNotFoundError:
            print("No grading.toml file found. Are you in the correct folder?")
            self.exit()

    def on_mount(self) -> None:
        def callback(result):
            self.assignments, self.students = result
            self.push_screen(AssignmentsScreen())

        self.app.push_screen(StartupScreen(), callback=callback)


def app():
    GradingTool().run()


if __name__ == "__main__":
    app()
