from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from canvas_course_tools.datatypes import Student as CanvasStudent
from textual import on
from textual.app import App, ComposeResult
from textual.command import Hit, Hits, Provider
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, ListItem, ListView, Static

from ecpcgrading.tasks import TasksScreen

if TYPE_CHECKING:
    from ecpcgrading.assignments import Assignment
    from ecpcgrading.tui import GradingTool


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
