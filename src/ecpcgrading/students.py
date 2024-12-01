from __future__ import annotations

import threading
import time
from functools import partial
from typing import TYPE_CHECKING

import humanize
from canvas_course_tools.datatypes import CanvasComment, CanvasSubmission
from canvas_course_tools.datatypes import Student as CanvasStudent
from textual import on, work
from textual.app import App, ComposeResult
from textual.command import Hit, Hits, Provider
from textual.containers import Horizontal, VerticalScroll
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Header, Label, ListItem, ListView, Static
from textual.worker import Worker, get_current_worker

from ecpcgrading.tasks import TasksScreen

if TYPE_CHECKING:
    from ecpcgrading.assignments import Assignment
    from ecpcgrading.tui import GradingTool

CANVAS_POOL_SIZE = 8


class CommentsScreen(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Dismiss comments")]

    def __init__(self, student_name: str, comments: list[CanvasComment]) -> None:
        super().__init__()
        self.student_name = student_name
        self.comments = comments

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="comments"):
            for comment in self.comments:
                content = f"[dim]On {comment.created_at.ctime()}, [not dim bold]{comment.author_name}[/] wrote:[/]\n\n"
                content += comment.comment
                if comment.author_name == self.student_name:
                    classes = "author"
                else:
                    classes = "other"
                yield Static(content, classes=classes)

    def on_mount(self) -> None:
        widget = self.query_one("#comments")
        widget.border_title = "Comments"
        widget.border_subtitle = "Escape to close"


class Student(ListItem):
    submission: reactive[CanvasSubmission | None] = reactive(None)

    def __init__(self, student: CanvasStudent) -> None:
        super().__init__()
        self._student = student
        self.student_name = student.name

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label(self.student_name)
            yield Label(id="comments")
            yield Label(id="grade")
            yield Label(id="status")

    def watch_submission(self) -> None:
        if self.submission:
            self.show_comments_count()
            self.show_grade()
            self.show_submission_status()

    def show_comments_count(self) -> None:
        author_count = len(
            [c for c in self.submission.comments if c.author_name == self.student_name]
        )
        other_count = len(self.submission.comments) - author_count
        match author_count, other_count:
            case 0, 0:
                text = ""
            case int(), 0:
                text = f"📝: [bold]{author_count}"
            case 0, int():
                text = f"📝:   [dim](+{other_count})"
            case int(), int():
                text = f"📝: [bold]{author_count}[/bold] [dim](+{other_count})"
        self.query_one("#comments", Label).update(text)

    def show_grade(self) -> None:
        match self.submission.grade:
            case "Fantastisch":
                text = "[bold bright_white]Fantastisch ✨"
            case "Goed":
                text = "[bold green]Goed ✅"
            case "Ontoereikend":
                text = "[bold bright_red]Ontoereikend ❌"
            case _:
                text = ""
        self.query_one("#grade", Label).update(text)

    def show_submission_status(self) -> None:
        if self.submission.attempt is None:
            if self.submission.seconds_late > 0:
                text = "[italic bold red](Not submitted)"
            else:
                text = "[italic bold orange1](Not yet submitted)"
        elif self.submission.attempts[-1].seconds_late == 0:
            text = "[italic bold green](On time)"
        elif self.submission.attempts[-1].seconds_late < 15 * 60:
            text = f"[italic bold orange1]({humanize.naturaldelta(self.submission.attempts[-1].seconds_late)})"
        else:
            text = f"[italic bold red]({humanize.naturaldelta(self.submission.attempts[-1].seconds_late)})"
        self.query_one("#status", Label).update(text)


class Students(ListView):
    BINDINGS = [("c", "show_comments", "Show comments")]

    def __init__(self, assignment: Assignment) -> None:
        super().__init__()
        self.assignment = assignment

    def compose(self) -> ComposeResult:
        for student in self.app.students:
            yield Student(student)

    def action_show_comments(self) -> None:
        student: Student = self.highlighted_child
        if student.submission:
            if student.submission.comments:
                self.app.push_screen(
                    CommentsScreen(student.student_name, student.submission.comments)
                )

    def on_list_item__child_clicked(self, event: ListItem._ChildClicked) -> None:
        if self.index != (clicked_index := self._nodes.index(event.item)):
            event.prevent_default()
            event.stop()
            self.index = clicked_index


class GradeStudentCommands(Provider):
    app: "GradingTool"

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        for student in self.screen.query_one(Students).children:
            command = f"grade {student.student_name}"
            score = matcher.match(command)
            if score > 0:
                yield Hit(
                    score,
                    matcher.highlight(command),
                    partial(self.screen.highlight_student, student),
                )


class StudentsScreen(Screen):
    BINDINGS = [("escape", "go_back", "Back to Assignments")]
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
        t0 = time.time()
        worker = get_current_worker()
        students = list(self.query(Student))
        batch_size, remainder = divmod(len(students), CANVAS_POOL_SIZE)
        if remainder:
            batch_size += 1
        threads = []
        for idx in range(0, len(students), batch_size):
            batch = students[idx : idx + batch_size]
            thread = threading.Thread(
                target=self.load_submission_info_task,
                kwargs=dict(assignment=self.assignment, students=batch, worker=worker),
            )
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        self.notify(f"Loaded submissions in {time.time() - t0:.1f} s.")

    def load_submission_info_task(
        self, assignment: Assignment, students: list[Student], worker: Worker
    ) -> None:
        for student in students:
            if not worker.is_cancelled:
                submission: CanvasSubmission = self.app.canvas_tasks.get_submissions(
                    assignment._assignment, student._student
                )
            if not worker.is_cancelled:
                student.submission = submission

    @on(Button.Pressed, "#back")
    def action_go_back(self) -> None:
        self.dismiss()

    @on(Students.Selected)
    def select_student(self, event: Students.Selected) -> None:
        self.show_tasks(event.item)

    def show_tasks(self, student: Student) -> None:
        self.app.push_screen(TasksScreen(self.assignment, student))

    def highlight_student(self, student: Student) -> None:
        students = self.query_one(Students)
        idx = students.children.index(student)
        students.index = idx
