from rest_framework.pagination import CursorPagination, PageNumberPagination


class DefaultPageNumberPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200


class AttendanceHistoryCursorPagination(CursorPagination):
    """`Attendance` history is the one cursor-paginated list — see
    docs/03-API-SPECIFICATION.md's Conventions section. `-attendance_date`
    is a valid cursor ordering because `UniqueConstraint(employee,
    attendance_date)` makes it monotonic *within a single employee's*
    queryset, which is the only way this pagination class is ever used.
    """

    page_size = 30
    ordering = "-attendance_date"
