"""Binds the Postgres session variable RLS policies key on — see
docs/01-SYSTEM-ARCHITECTURE.md §6.3 ("last-resort" defense-in-depth layer
below the ORM-level `TenantManager` and above nothing; if this and the
manager both fail, the policy is the only thing left).

A no-op everywhere the active connection isn't Postgres (local/dev/most
test runs use SQLite per .env.example's default `DATABASE_URL`) — RLS
itself only exists on the Postgres side, so binding a session variable
against SQLite would be meaningless, not merely inert.

Uses session-level `set_config` (`is_local=false`), not `SET LOCAL`,
because Django does not wrap requests in a transaction by default
(`ATOMIC_REQUESTS` is off) — a transaction-local `SET LOCAL` would silently
stop applying after the first auto-committed statement. Session-level
scoping is safe here because `ResetTenantContextMiddleware` clears it at
the start of every request, mirroring how it resets the `contextvars`
right beside it, so a value can never leak from one request into the next
even on a reused pooled connection.

Three distinct states, not two — this is the part easy to get wrong:
  - unbound/reset (empty string): fail closed, a policy sees this and
    grants nothing. Used at the start of every request, and for anything
    that never goes through `TenantAwareJWTAuthentication` at all (a
    forgotten context is the exact bug this whole layer exists to catch).
  - a concrete organization UUID: the common case, one tenant.
  - `WILDCARD` ("platform-wide", used only for `role=SUPER_ADMIN`):
    Super Admin JWTs carry `organization_id: null`, which is *not* the
    same thing as "unbound" — it's a token that legitimately needs to
    read across every organization (e.g. the system-wide audit log,
    or `Organization.current_subscription` computed for an arbitrary
    org from a platform endpoint). `FORCE ROW LEVEL SECURITY` applies at
    the DB-role level, not per Django manager — so `.all_tenants()`
    calling code is *not* enough on its own to grant that access once RLS
    is on; the policy itself has to know the difference between "nobody
    told me who's asking" and "the platform owner is asking, on purpose."
    Collapsing this into the plain "no org" case would silently break
    every legitimate Super Admin cross-org read the day RLS was enabled.
"""

from django.db import connection

_SESSION_VAR = "app.current_org_id"
WILDCARD = "*"


def bind(*, organization_id=None, platform_wide=False):
    if connection.vendor != "postgresql":
        return
    if platform_wide:
        value = WILDCARD
    elif organization_id:
        value = str(organization_id)
    else:
        value = ""
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config(%s, %s, false)", [_SESSION_VAR, value])


def reset():
    bind()


def bind_for_user(user):
    """Binds both the tenant contextvars and the RLS session for `user` —
    shared by `TenantAwareJWTAuthentication` (every subsequent
    JWT-authenticated request) and the login flow itself
    (`apps.authentication.services.authenticate`).

    Login needs this too: a freshly-authenticated user's own tenant-scoped
    data (e.g. their nested `employee` profile serialized straight into the
    login response) must be readable in the *same* request that issues
    their first token — there is no JWT yet for
    `TenantAwareJWTAuthentication` to have bound anything from, and without
    this, that first read fails closed under Postgres RLS exactly like any
    other unbound session, even though the user just proved who they are.
    """
    from apps.authentication.models import Role
    from core.middleware.tenant_context import current_organization_id, current_role

    current_organization_id.set(str(user.organization_id) if user.organization_id else None)
    current_role.set(user.role)
    bind(organization_id=user.organization_id, platform_wide=user.role == Role.SUPER_ADMIN)
