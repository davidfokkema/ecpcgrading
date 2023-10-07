from canvas_course_tools import utils
from canvas_course_tools.datatypes import Assignment


def get_assignments(server: str, course_id: int) -> list[Assignment]:
    """Get ECPC assignments from Canvas

    Get all assignments from the ECPC assignment group for the specified course
    from the Canvas server.

    Args:
        server (str): the Canvas server
        course_id (int): the course id for which to fetch the assignments

    Returns:
        list[Assignment]: a list of assignments
    """
    canvas = utils.get_canvas(server)
    course = canvas.get_course(course_id)
    assignment_groups = canvas.get_assignment_groups(course)
    ecpc = next(group for group in assignment_groups if group.name == "ECPC")
    return canvas.get_assignments_for_group(ecpc)
