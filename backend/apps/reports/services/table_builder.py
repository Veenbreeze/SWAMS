"""Flattens each report type's aggregation result into a uniform
`(headers, rows)` table shape — the one place that needs to know each
report's specific structure, so both exporters
(apps/reports/services/exporters/{pdf,excel}.py) stay format-agnostic.
"""

_RANGE_HEADERS = ["Date", "Present", "Late", "Early Departure", "Overtime", "Absent"]


def _day_row(day):
    return [
        day["date"],
        day["present"],
        day["late"],
        day["early_departure"],
        day["overtime"],
        day["absent"] if day["absent"] is not None else "-",
    ]


def range_summary_table(data):
    rows = [_day_row(day) for day in data["days"]]
    totals = data["totals"]
    rows.append(
        [
            "TOTAL",
            totals["present"],
            totals["late"],
            totals["early_departure"],
            totals["overtime"],
            totals["absent"],
        ]
    )
    return _RANGE_HEADERS, rows


def daily_summary_table(data):
    headers = ["Metric", "Value"]
    rows = [
        ["Date", data["date"]],
        ["Working Day", "Yes" if data["is_working_day"] else "No"],
        ["Total Employees", data["total_employees"]],
        ["Present", data["present"]],
        ["Late", data["late"]],
        ["Early Departure", data["early_departure"]],
        ["Overtime", data["overtime"]],
        ["Absent", data["absent"] if data["absent"] is not None else "-"],
    ]
    return headers, rows


def attendance_records_table(records):
    headers = [
        "Employee",
        "Date",
        "Status",
        "Check In",
        "Check Out",
        "Late (min)",
        "Overtime (min)",
    ]
    rows = [
        [
            record.employee.full_name,
            record.attendance_date,
            record.status,
            record.check_in_time.isoformat() if record.check_in_time else "-",
            record.check_out_time.isoformat() if record.check_out_time else "-",
            record.late_minutes,
            record.overtime_minutes,
        ]
        for record in records
    ]
    return headers, rows


def employee_report_table(report):
    headers = ["Date", "Status", "Working Minutes", "Late Minutes", "Overtime Minutes"]
    rows = [
        [r.attendance_date, r.status, r.working_minutes, r.late_minutes, r.overtime_minutes]
        for r in report["records"]
    ]
    return headers, rows
