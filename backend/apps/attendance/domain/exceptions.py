"""Domain-level check-in/check-out failures — plain Python exceptions, no
framework import, so `application/services.py` (or a future non-HTTP
caller) can catch/handle them without pulling in DRF. Each carries the
stable `code` docs/03-API-SPECIFICATION.md's error envelope expects; the
interfaces layer maps `code`/message onto `core.exceptions.ApiError`.
"""


class AttendanceDomainError(Exception):
    code = "ATTENDANCE_ERROR"
    status_code = 400
    default_message = "Unable to process this attendance request."

    def __init__(self, message=None):
        self.message = message or self.default_message
        super().__init__(self.message)


class NoBranchAssignedError(AttendanceDomainError):
    code = "NO_BRANCH_ASSIGNED"
    status_code = 422
    default_message = "You have not been assigned a branch to check in at."


class OutsideGeofenceError(AttendanceDomainError):
    code = "OUTSIDE_GEOFENCE"
    status_code = 422
    default_message = "You are outside the authorized workplace location."


class PoorGpsAccuracyError(AttendanceDomainError):
    code = "POOR_GPS_ACCURACY"
    status_code = 422
    default_message = "Unable to verify your location. Please move to an open area and try again."


class MockLocationDetectedError(AttendanceDomainError):
    code = "MOCK_LOCATION_DETECTED"
    status_code = 422
    # Deliberately generic — does not reveal detection to a would-be
    # spoofer, per docs/01-SYSTEM-ARCHITECTURE.md §6.6.
    default_message = "Unable to verify your location. Please move to an open area and try again."


class AlreadyCheckedInError(AttendanceDomainError):
    code = "ALREADY_CHECKED_IN"
    status_code = 409
    default_message = "You have already checked in today."


class NotCheckedInYetError(AttendanceDomainError):
    code = "NOT_CHECKED_IN_YET"
    status_code = 400
    default_message = "You have not checked in yet today."


class AlreadyCheckedOutError(AttendanceDomainError):
    code = "ALREADY_CHECKED_OUT"
    status_code = 409
    default_message = "You have already checked out today."
