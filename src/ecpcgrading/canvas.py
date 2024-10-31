from canvas_course_tools.canvas_tasks import CanvasTasks
from canvas_course_tools.datatypes import Assignment, Course, Student
from unidecode import unidecode


def get_assignments(
    canvas_tasks: CanvasTasks, course: Course, group_name: str
) -> list[Assignment]:
    """Get ECPC assignments from Canvas

    Get all assignments from the ECPC assignment group for the specified course
    from the Canvas server.

    Args:
        canvas_tasks (CanvasTasks): a CanvasTasks instance
        course (Course): the course object containing the assignments
        group_name (str): the name of the assignment group

    Returns:
        list[Assignment]: a list of assignments
    """
    assignment_groups = canvas_tasks.get_assignment_groups(course)
    try:
        ecpc = next(group for group in assignment_groups if group.name == group_name)
    except StopIteration:
        raise RuntimeError(f"Assignment group {group_name} not found.")
    else:
        assignments = canvas_tasks.get_assignments_for_group(ecpc)
        return [a for a in assignments if "online_upload" in a.submission_types]


def get_students(
    canvas_tasks: CanvasTasks,
    course: Course,
    groupset_name: str | None,
    group_name: str | None,
) -> list[Student]:
    match groupset_name, group_name:
        case (str(), str()):
            groupset = get_groupset_by_name(groupset_name, canvas_tasks, course)
            group = get_group_from_groupset_by_name(group_name, canvas_tasks, groupset)
            return canvas_tasks.get_students_in_group(group)
        case (str(), None):
            students = []
            groupset = get_groupset_by_name(groupset_name, canvas_tasks, course)
            for group in canvas_tasks.list_groups(groupset):
                students.extend(canvas_tasks.get_students_in_group(group))
            return sorted(
                students, key=lambda x: unidecode(getattr(x, "sortable_name"))
            )
        case (None, str()):
            raise RuntimeError(f"Group {group_name} specified without 'groupset'")
        case _:
            return canvas_tasks.get_students(
                course_id=course.id, show_test_student=True
            )


def get_groupset_by_name(groupset_name, canvas, course):
    groupsets = canvas.list_groupsets(course)
    try:
        groupset = next(g for g in groupsets if g.name == groupset_name)
    except StopIteration:
        raise RuntimeError(f"Group set {groupset_name} not found")
    return groupset


def get_group_from_groupset_by_name(group_name, canvas, groupset):
    groups = canvas.list_groups(groupset)
    try:
        group = next(g for g in groups if g.name == group_name)
    except StopIteration:
        raise RuntimeError(f"Group {group_name} not found in group set {groupset.name}")
    return group
