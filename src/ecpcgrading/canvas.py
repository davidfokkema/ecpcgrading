from canvas_course_tools import utils
from canvas_course_tools.datatypes import Assignment, Student


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
    server: str, course_id: int, groupset_name: str, group_name: str
) -> list[Student]:
    canvas = utils.get_canvas(server)
    course = canvas.get_course(course_id)
    groupsets = canvas.list_groupsets(course)
    groupset = next(g for g in groupsets if g.name == groupset_name)
    groups = canvas.list_groups(groupset)
    group = next(g for g in groups if g.name == group_name)
    return canvas.get_students_in_group(group)
