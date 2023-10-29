from functools import partial
from pathlib import Path

from canvas_course_tools.canvas_tasks import CanvasTasks
from canvas_course_tools.datatypes import Assignment as CanvasAssignment
from canvas_course_tools.datatypes import Course as CanvasCourse
from canvas_course_tools.datatypes import Student as CanvasStudent
from canvas_course_tools.utils import find_course
from textual import on, work
from textual.app import App, ComposeResult
from textual.command import Hit, Hits, Provider
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

import ecpcgrading.config
from ecpcgrading import canvas, tasks


class Assignment(ListItem):
    def __init__(self, assignment: CanvasAssignment) -> None:
        super().__init__()
        self._assignment = assignment
        self.title = assignment.name

    def compose(self) -> ComposeResult:
        yield Label(self.title)


class Assignments(ListView):
    def compose(self) -> ComposeResult:
        for assignment in self.app.assignments:
            yield Assignment(assignment)

    def on_list_view_selected(self, event: "Assignments.Selected") -> None:
        assignment: Assignment = event.item
        self.app.push_screen(StudentsScreen(assignment))


class AssignmentsScreen(Screen):
    app: "GradingTool"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Horizontal(
            Button(".", id="back", disabled=True),
            Static("", id="spacer"),
            id="breadcrumbs",
        )
        yield Label(
            f"{self.app.course.name} - {self.app.course.term}", id="course_info"
        )
        yield Label("Please Select an Assignment", id="list_header")
        yield Assignments(id="assignments")

    def on_mount(self) -> None:
        self.query_one("Assignments").focus()


class Student(ListItem):
    def __init__(self, student: CanvasStudent) -> None:
        super().__init__()
        self._student = student
        self.student_name = student.name

    def compose(self) -> ComposeResult:
        yield Label(self.student_name)


class Students(ListView):
    def __init__(self, assignment: Assignment) -> None:
        super().__init__()
        self.assignment = assignment

    def compose(self) -> ComposeResult:
        for student in self.app.students:
            yield Student(student)


class GradeStudentCommands(Provider):
    app: "GradingTool"

    async def search(self, query: str) -> Hits:
        print("FOO")
        matcher = self.matcher(query)
        for student in self.app.students:
            command = f"grade {student.name}"
            score = matcher.match(command)
            if score > 0:
                yield Hit(
                    score,
                    matcher.highlight(command),
                    partial(self.screen.show_tasks, Student(student)),
                )


class StudentsScreen(Screen):
    BINDINGS = [("b", "go_back", "Back to Assignments")]
    COMMANDS = App.COMMANDS | {GradeStudentCommands}

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

    @on(Students.Selected)
    def select_student(self, event: Students.Selected) -> None:
        self.show_tasks(event.item)

    def show_tasks(self, student: Student) -> None:
        self.app.push_screen(TasksScreen(self.assignment, student))


class Tasks(ListView):
    app: "GradingTool"

    def __init__(self, assignment: Assignment, student: Student) -> None:
        super().__init__()
        self.assignment = assignment
        self.student = student

    def compose(self) -> ComposeResult:
        yield tasks.DownloadTask("Download Submission")
        yield tasks.UncompressCodeTask("Extract submission into grading folder")
        for env in self.app.config.env.values():
            yield tasks.CreateEnvTask(f"Create conda environment: {env.name}", env=env)
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
