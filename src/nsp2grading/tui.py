from faker import Faker
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Label


class Assignment(Label):
    def __init__(self, title):
        super().__init__()
        self.title = title
        self.update(self.title)


class Assignments(VerticalScroll):
    def compose(self) -> ComposeResult:
        fake = Faker()
        fake.seed_instance(0)
        for assignment in [fake.sentence() for _ in range(5)]:
            yield Assignment(assignment)


class AssignmentsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Assignments()


class GradingTool(App):
    TITLE = "Grading Tool for ECPC"
    CSS_PATH = "grading_tool.css"

    def on_mount(self) -> None:
        self.push_screen(AssignmentsScreen())


if __name__ == "__main__":
    app = GradingTool()
    app.run()
