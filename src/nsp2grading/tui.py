import time
from collections.abc import Callable

from faker import Faker
from textual import on, work
from textual.app import App, ComposeResult
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


class Assignment(ListItem):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.title = title

    def compose(self) -> ComposeResult:
        yield Label(self.title)


class Assignments(ListView):
    def compose(self) -> ComposeResult:
        assignments = [
            "Pythondaq met Poetry",
            "Click: smallangle",
            "Pythondaq met Click",
            "GUI: functieplotter",
            "Pythondaq met GUI",
        ]
        for assignment in assignments:
            yield Assignment(assignment)

    def on_list_view_selected(self, event: "Assignments.Selected") -> None:
        assignment: Assignment = event.item
        self.app.push_screen(StudentsScreen(assignment))


class AssignmentsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Horizontal(
            Button(".", id="back", disabled=True),
            Static("", id="spacer"),
            id="breadcrumbs",
        )
        yield Label("Please Select an Assignment", id="list_header")
        yield Assignments(id="assignments")

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


class Task(ListItem):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.title = title

    def compose(self) -> ComposeResult:
        yield Label(self.title)

    def execute(self) -> None:
        ...


class RunTaskModal(ModalScreen):
    def __init__(
        self,
        task: Callable[[], None],
        msg: str,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)
        self.task_ = task
        self.msg = msg

    def compose(self) -> ComposeResult:
        with Vertical(id="modal_dialog"):
            with Center():
                yield Label(self.msg)
            yield LoadingIndicator()

    async def on_mount(self) -> None:
        self.task_()


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
                yield Label(f"{self.msg}: {self.exception}")
            with Center():
                yield Button("Close", variant="primary")

    @on(Button.Pressed)
    def close_dialog(self, event: Button.Pressed) -> None:
        self.dismiss()


class DownloadTask(Task):
    def execute(self) -> None:
        print("Downloading submission!")
        self.app.push_screen(
            RunTaskModal(self.run_download, "Downloading assignment...")
        )

    @work(thread=True, exit_on_error=False)
    def run_download(self):
        for _ in range(3):
            print("WORK")
            # 1 / 0
            time.sleep(1)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        print("STATE CHANGED")
        if event.state == WorkerState.SUCCESS:
            self.app.pop_screen()
        elif event.state == WorkerState.ERROR:
            self.app.pop_screen()
            self.app.push_screen(
                TaskErrorModal("Download failed", exception=event.worker.error)
            )


class UnpackTask(Task):
    def execute(self) -> None:
        print("Unpacking submission!")


class CreateEnvTask(Task):
    def execute(self) -> None:
        print("CREATING CONDA ENV!")


class OpenCodeTask(Task):
    def execute(self) -> None:
        print("Opening Visual Studio Code!")


class Tasks(ListView):
    def __init__(self, assignment: Assignment, student: Student) -> None:
        super().__init__()
        self.assignment = assignment
        self.student = student

    def compose(self) -> ComposeResult:
        yield DownloadTask("Download Submission")
        yield UnpackTask("Unpack submission into grading folder")
        yield CreateEnvTask("(Re)create an empty conda environment")
        yield OpenCodeTask("Open Visual Studio Code")

    @on(ListView.Selected)
    def execute_task(self, selected: ListView.Selected) -> None:
        selected.item.execute()


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
    CSS_PATH = "grading_tool.css"
    BINDINGS = [("q", "quit", "Quit")]

    def on_mount(self) -> None:
        self.push_screen(AssignmentsScreen())


if __name__ == "__main__":
    app = GradingTool()
    app.run()
