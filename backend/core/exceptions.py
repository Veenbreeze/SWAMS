"""Uniform API error envelope.

Every error response from the API takes the shape documented in
docs/03-API-SPECIFICATION.md:

    { "error": { "code": "...", "message": "...", "details": {} } }

`code` is stable and machine-readable (clients switch/localize on it);
`message` is a default-locale human string, not a localization contract.
"""

from rest_framework.views import exception_handler as drf_exception_handler


class ApiError(Exception):
    """Raise from domain/application/view code to produce a specific,
    documented error code instead of a generic 400/500."""

    status_code = 400
    code = "ERROR"
    default_message = "Something went wrong."

    def __init__(self, message=None, details=None, code=None, status_code=None):
        self.message = message or self.default_message
        self.details = details or {}
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        super().__init__(self.message)


def uniform_exception_handler(exc, context):
    if isinstance(exc, ApiError):
        from rest_framework.response import Response

        return Response(
            {"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
            status=exc.status_code,
        )

    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    code = getattr(exc, "default_code", None) or "ERROR"
    if isinstance(response.data, dict) and "detail" in response.data:
        message = str(response.data["detail"])
        details = {}
    else:
        message = "Validation failed."
        details = response.data
        code = "VALIDATION_ERROR"

    response.data = {"error": {"code": str(code).upper(), "message": message, "details": details}}
    return response
