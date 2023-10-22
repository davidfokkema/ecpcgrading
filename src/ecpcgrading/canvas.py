from canvas_course_tools import utils
from canvas_course_tools.datatypes import Assignment, Student
from unidecode import unidecode


def get_assignments(server: str, course_id: int, group_name: str) -> list[Assignment]:
    """Get ECPC assignments from Canvas

    Get all assignments from the ECPC assignment group for the specified course
    from the Canvas server.

    Args:
        server (str): the Canvas server
        course_id (int): the course id for which to fetch the assignments
        group_name (str): the name of the assignment group

    Returns:
        list[Assignment]: a list of assignments
    """
    canvas = utils.get_canvas(server)
    course = canvas.get_course(course_id)
    assignment_groups = canvas.get_assignment_groups(course)
    ecpc = next(group for group in assignment_groups if group.name == group_name)
    return canvas.get_assignments_for_group(ecpc)


def get_students(
    server: str, course_id: int, groupset_name: str | None, group_name: str | None
) -> list[Student]:
    canvas = utils.get_canvas(server)
    course = canvas.get_course(course_id)

    match groupset_name, group_name:
        case (str(), str()):
            groupset = get_groupset_by_name(groupset_name, canvas, course)
            group = get_group_from_groupset_by_name(group_name, canvas, groupset)
            return canvas.get_students_in_group(group)
        case (str(), None):
            students = []
            groupset = get_groupset_by_name(groupset_name, canvas, course)
            for group in canvas.list_groups(groupset):
                students.extend(canvas.get_students_in_group(group))
            return sorted(
                students, key=lambda x: unidecode(getattr(x, "sortable_name"))
            )
        case (None, str()):
            raise RuntimeError(f"Group {group_name} specified without 'groupset'")
        case _:
            return canvas.get_students(course_id=course.id)


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