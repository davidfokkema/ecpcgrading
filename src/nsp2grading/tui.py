import time
from pathlib import Path

from faker import Faker
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, ListItem, ListView, Static
from textual.worker import Worker, WorkerState

import nsp2grading.config
from nsp2grading import tasks


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
            yield Assignment(assignment)

    def on_list_view_selected(self, event: "Assignments.Selected") -> None:
        assignment: Assignment = event.item
        self.app.push_screen(StudentsScreen(assignment))


class AssignmentsScreen(Screen):
    def on_compose(self) -> None:
        self.app.push_screen(tasks.RunTaskModal("Fetching assignments..."))
        self.get_assignments()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Horizontal(
            Button(".", id="back", disabled=True),
            Static("", id="spacer"),
            id="breadcrumbs",
        )
        yield Label("Please Select an Assignment", id="list_header")

    @on(Worker.StateChanged)
    def show_assignments(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.SUCCESS:
            assignments = event.worker.result
            self.mount(Assignments(assignments, id="assignments"))
            self.query_one("Assignments").focus()
            self.app.pop_screen()

    @work(thread=True)
    def get_assignments(self) -> list[str]:
        assignments = [
            "Pythondaq met Poetry",
            "Click: smallangle",
            "Pythondaq met Click",
            "GUI: functieplotter",
            "Pythondaq met GUI",
        ]
        time.sleep(3)
        return assignments


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


class GradingTool(App):
    TITLE = "Grading Tool for ECPC"
    CSS_PATH = "grading_tool.tcss"
    BINDINGS = [("q", "quit", "Quit")]

    config: nsp2grading.config.Config

    def __init__(self):
        super().__init__()
        self.config = nsp2grading.config.read_config(Path.cwd())

    def on_mount(self) -> None:
        self.push_screen(AssignmentsScreen())


if __name__ == "__main__":
    app = GradingTool()
    app.run()
