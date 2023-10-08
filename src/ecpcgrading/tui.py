from pathlib import Path

from canvas_course_tools.datatypes import Assignment as CanvasAssignment
from faker import Faker
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Center, Horizontal, Vertical
from textual.reactive import reactive
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

import ecpcgrading.config
from ecpcgrading import canvas, tasks


class Assignment(ListItem):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.title = title

    def compose(self) -> ComposeResult:
        yield Label(self.title)


class Assignments(ListView):
    def __init__(self, assignments: list[str], id: str | None = None) -> None:
        super().__init__()
        self.assignments = assignments

    def compose(self) -> ComposeResult:
        for assignment in self.assignments:
            yield Assignment(assignment.name)

    def on_list_view_selected(self, event: "Assignments.Selected") -> None:
        assignment: Assignment = event.item
        self.app.push_screen(StudentsScreen(assignment))


class AssignmentsScreen(Screen):
    def __init__(
        self,
        assignments: list[CanvasAssignment],
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)
        self.assignments = assignments

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Horizontal(
            Button(".", id="back", disabled=True),
            Static("", id="spacer"),
            id="breadcrumbs",
        )
        yield Label("Please Select an Assignment", id="list_header")
        yield Assignments(self.assignments, id="assignments")

    def on_mount(self) -> None:
        self.query_one("Assignments").focus()


class Student(ListItem):
    def __init__(self, student: str) -> None:
        super().__init__()
        self.student_name = student

    def compose(self) -> ComposeResult:
        yield Label(self.student_name)


class Students(ListView):
    def __init__(self, assignment: Assignment) -> None:
        super().__init__()
        self.assignment = assignment

    def compose(self) -> ComposeResult:
        fake = Faker(locale="nl")
        fake.seed_instance(1)
        for student in [fake.name() for _ in range(10)]:
            yield Student(student)

    def on_list_view_selected(self, event: "Students.Selected") -> None:
        student: Student = event.item
        self.app.push_screen(TasksScreen(self.assignment, student))


class StudentsScreen(Screen):
    BINDINGS = [("b", "go_back", "Back to Assignments")]

    def __init__(self, assignment: Assignment) -> None:
        super().__init__()
        self.assignment = assignment

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Horizontal(
            Button("< Assignments", id="back"),
            Static("", id="spacer"),
            Label(self.assignment.title),
            id="breadcrumbs",
        )
        yield Label("Please Select a Student", id="list_header")
        yield Students(self.assignment)

    def on_mount(self) -> None:
        self.query_one("Students").focus()

    @on(Button.Pressed, "#back")
    def action_go_back(self) -> None:
        self.dismiss()


class Tasks(ListView):
    def __init__(self, assignment: Assignment, student: Student) -> None:
        super().__init__()
        self.assignment = assignment
        self.student = student

    def compose(self) -> ComposeResult:
        yield tasks.DownloadTask("Download Submission")
        yield tasks.UncompressCodeTask("Extract submission into grading folder")
        yield tasks.CreateEnvTask("(Re)create an empty conda environment")
        yield tasks.OpenCodeTask("Open Visual Studio Code")

    @on(ListView.Selected)
    def execute_task(self, selected: ListView.Selected) -> None:
        selected.item.execute(self.assignment, self.student)


class TasksScreen(Screen):
    BINDINGS = [("b", "go_back", "Back to Students")]

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


class StartupScreen(ModalScreen):
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
        assignments = canvas.get_assignments(config.server, config.course_id)
        # students = canvas.get_students(config.server, config.course_id)
        return assignments

    @on(Worker.StateChanged)
    def return_assignments(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.SUCCESS:
            assignments = event.worker.result
            self.dismiss(assignments)


class GradingTool(App):
    TITLE = "Grading Tool for ECPC"
    CSS_PATH = "grading_tool.tcss"
    BINDINGS = [("q", "quit", "Quit")]

    config: ecpcgrading.config.Config

    def __init__(self):
        super().__init__()
        self.config = ecpcgrading.config.read_config(Path.cwd())

    def on_mount(self) -> None:
        def callback(result):
            self.assignments = result
            self.push_screen(AssignmentsScreen(self.assignments))

        self.app.push_screen(StartupScreen(), callback=callback)


if __name__ == "__main__":
    app = GradingTool()
    app.run()
