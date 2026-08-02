"""Request-scoped tenant context — see docs/01-SYSTEM-ARCHITECTURE.md §4.1.

Uses contextvars (not thread-locals) so it stays correct under async views
and Celery workers, not just sync WSGI threads.
"""

import contextvars

current_organization_id = contextvars.ContextVar("current_organization_id", default=None)
current_role = contextvars.ContextVar("current_role", default=None)
