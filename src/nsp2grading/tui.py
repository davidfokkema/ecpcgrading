from faker import Faker
from textual import on
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, ListItem, ListView


class Assignment(ListItem):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.title = title

    def compose(self) -> ComposeResult:
        yield Label(self.title)


class Assignments(ListView):
    def compose(self) -> ComposeResult:
        fake = Faker()
        fake.seed_instance(0)
        for assignment in [fake.sentence() for _ in range(5)]:
            yield Assignment(assignment)

    def on_list_view_selected(self, event: "Assignments.Selected") -> None:
        assignment: Assignment = event.item
        self.app.push_screen(StudentsScreen(assignment))


class AssignmentsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Button(".", id="back", disabled=True)
        yield Label("Please Select an Assignment", id="list_header")
        yield Assignments(id="assignments")

    def on_mount(self) -> None:
        self.query_one("Assignments").focus()


class Student(ListItem):
    def __init__(self, student: str) -> None:
        super().__init__()
        self.student = student

    def compose(self) -> ComposeResult:
        yield Label(self.student)


class Students(ListView):
    def __init__(self, assignment: Assignment) -> None:
        super().__init__()
        self.assignment = assignment

    def compose(self) -> ComposeResult:
        fake = Faker()
        fake.seed_instance(0)
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
        yield Button("< Assignments", id="back")
        yield Label("Please Select a Student", id="list_header")
        yield Students(self.assignment)

    def on_mount(self) -> None:
        self.query_one("Students").focus()

    @on(Button.Pressed, "#back")
    def action_go_back(self) -> None:
        self.dismiss()


class Task(ListItem):
    def __init__(self, label: str, title: str) -> None:
        super().__init__()
        self.label = label
        self.title = title

    def compose(self) -> ComposeResult:
        yield Label(self.title)


class Tasks(ListView):
    def __init__(self, assignment: Assignment, student: Student) -> None:
        super().__init__()
        self.assignment = assignment
        self.student = student

    def compose(self) -> ComposeResult:
        yield Task("download", "Download Submission")
        yield Task("unpack", "Unpack submission into grading folder")
        yield Task("create_env", "(Re)create an empty conda environment")
        yield Task("vscode", "Open Visual Studio Code")


class TasksScreen(Screen):
    BINDINGS = [("b", "go_back", "Back to Students")]

    def __init__(self, assignment: Assignment, student: Student) -> None:
        super().__init__()
        self.assignment = assignment
        self.student = student

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Button("< Students", id="back")
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
