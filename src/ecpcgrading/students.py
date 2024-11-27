from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

import humanize
from canvas_course_tools.datatypes import CanvasSubmission
from canvas_course_tools.datatypes import Student as CanvasStudent
from textual import on, work
from textual.app import App, ComposeResult
from textual.command import Hit, Hits, Provider
from textual.containers import Horizontal
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, ListItem, ListView, Static

from ecpcgrading.tasks import TasksScreen

if TYPE_CHECKING:
    from ecpcgrading.assignments import Assignment
    from ecpcgrading.tui import GradingTool


class Student(ListItem):
    # status = reactive
    def __init__(self, student: CanvasStudent) -> None:
        super().__init__()
        self._student = student
        self.student_name = student.name

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label(self.student_name)
            yield Label(id="comments")
            yield Label(id="grade")
            yield Label(id="submission_info")


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

    app: GradingTool

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
        self.load_submission_info()

    @work(thread=True)
    def load_submission_info(self) -> None:
        for student in self.query(Student):
            submission: CanvasSubmission = self.app.canvas_tasks.get_submissions(
                self.assignment._assignment, student._student
            )
            self.show_comments_count(student, submission)
            self.show_grade(student, submission)
            self.show_submission_status(student, submission)

    def show_comments_count(
        self, student: Student, submission: CanvasSubmission
    ) -> None:
        author_count = len(
            [c for c in submission.comments if c.author_name == student.student_name]
        )
        other_count = len(submission.comments) - author_count
        match author_count, other_count:
            case 0, 0:
                text = ""
            case int(), 0:
                text = f"📝: [bold]{author_count}"
            case 0, int():
                text = f"📝:   [dim](+{other_count})"
            case int(), int():
                text = f"📝: [bold]{author_count}[/bold] [dim](+{other_count})"
        try:
            widget = student.query_one("#comments")
        except NoMatches:
            # may happen when the user dismisses the student view but the
            # worker is not yet fully cancelled
            pass
        else:
            self.app.call_from_thread(widget.update, text)

    def show_grade(self, student: Student, submission: CanvasSubmission) -> None:
        match submission.grade:
            case "Fantastisch":
                grade_text = "[bold bright_white]Fantastisch ✨"
            case "Goed":
                grade_text = "[bold green]Goed ✅"
            case "Ontoereikend":
                grade_text = "[bold bright_red]Ontoereikend ❌"
            case _:
                grade_text = ""

        try:
            widget = student.query_one("#grade")
        except NoMatches:
            # may happen when the user dismisses the student view but the
            # worker is not yet fully cancelled
            pass
        else:
            self.app.call_from_thread(widget.update, grade_text)

    def show_submission_status(
        self, student: Student, submission: CanvasSubmission
    ) -> None:
        if submission.attempt is None:
            if submission.seconds_late > 0:
                status = "[italic bold red](Not submitted)"
            else:
                status = "[italic bold orange1](Not yet submitted)"
        elif submission.attempts[-1].seconds_late == 0:
            status = "[italic bold green](On time)"
        elif submission.attempts[-1].seconds_late < 15 * 60:
            status = f"[italic bold orange1]({humanize.naturaldelta(submission.attempts[-1].seconds_late)})"
        else:
            status = f"[italic bold red]({humanize.naturaldelta(submission.attempts[-1].seconds_late)})"

        try:
            info_widget = student.query_one("#submission_info")
        except NoMatches:
            # may happen when the user dismisses the student view but the
            # worker is not yet fully cancelled
            pass
        else:
            self.app.call_from_thread(info_widget.update, status)

    @on(Button.Pressed, "#back")
    def action_go_back(self) -> None:
        self.dismiss()

    @on(Students.Selected)
    def select_student(self, event: Students.Selected) -> None:
        self.show_tasks(event.item)

    def show_tasks(self, student: Student) -> None:
        self.app.push_screen(TasksScreen(self.assignment, student))
