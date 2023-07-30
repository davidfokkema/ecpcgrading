from faker import Faker
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, ListItem, ListView


class Assignment(ListItem):
    def __init__(self, title):
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
        self.app.push_screen(StudentsScreen())


class AssignmentsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Label(".", id="back")
        yield Label("Please Select an Assignment", id="list_header")
        yield Assignments()


class Student(ListItem):
    def __init__(self, student):
        super().__init__()
        self.student = student

    def compose(self) -> ComposeResult:
        yield Label(self.student)


class Students(ListView):
    def compose(self) -> ComposeResult:
        fake = Faker()
        fake.seed_instance(0)
        for student in [fake.name() for _ in range(10)]:
            yield Student(student)


class StudentsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Label("< Assignments", id="back")
        yield Label("Please Select a Student", id="list_header")
        yield Students()


class GradingTool(App):
    TITLE = "Grading Tool for ECPC"
    CSS_PATH = "grading_tool.css"

    def on_mount(self) -> None:
        self.push_screen(AssignmentsScreen())


if __name__ == "__main__":
    app = GradingTool()
    app.run()
