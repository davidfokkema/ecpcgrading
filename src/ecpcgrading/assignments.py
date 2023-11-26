from __future__ import annotations

from typing import TYPE_CHECKING

from canvas_course_tools.datatypes import Assignment as CanvasAssignment
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, ListItem, ListView, Static

from ecpcgrading.students import StudentsScreen

if TYPE_CHECKING:
    from ecpcgrading.tui import GradingTool


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
