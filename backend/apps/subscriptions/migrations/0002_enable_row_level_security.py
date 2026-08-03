"""Postgres RLS as defense-in-depth below the ORM's `TenantManager` — see
docs/01-SYSTEM-ARCHITECTURE.md §6.3 and core/db/rls.py.

Only a SELECT policy is restrictive. INSERT/UPDATE/DELETE stay permissive
(`USING (true)`/`WITH CHECK (true)`) deliberately: legitimate cross-tenant
writes are routine here — a Super Admin creating an organization's first
Subscription, or a Celery job renewing subscriptions across every
organization, runs with no single `app.current_org_id` bound (Super Admin
JWTs carry `organization_id: null`) or with one that legitimately differs
from the row being written. Write-path tenant correctness is enforced by
explicit application code (`organization=` set at creation, never inferred
from ambient session state); RLS's job here is narrowly to stop a *read*
that bypasses the ORM manager (a raw SQL query, a forgotten `.filter()`,
a bug in a future report query) from leaking cross-tenant rows — exactly
the scenario docs/05-DEVELOPMENT-ROADMAP.md's Phase 3 acceptance test
targets.

The SELECT policy recognizes `core.db.rls.WILDCARD` ("*") as "platform-wide
read, on purpose" (bound only for `role=SUPER_ADMIN`) alongside a matching
organization UUID — without it, `FORCE ROW LEVEL SECURITY` would block
every legitimate Super Admin cross-org read (e.g. viewing a specific org's
subscription from a platform endpoint) the moment RLS is enabled, since
RLS applies at the DB-role level and has no notion of `.all_tenants()`.

Compares `organization_id::text` against the session var rather than
casting the session var to `uuid` — confirmed against a real Postgres
instance that `current_setting(...) = '*' OR organization_id = NULLIF(...)
::uuid` is NOT safely short-circuited: Postgres does not guarantee the
second operand of a row-level-security `OR` is skipped once the first is
true, so `NULLIF('*', '')::uuid` was raising `invalid input syntax for
type uuid` on every Super Admin (WILDCARD) read of an org-scoped row.
Casting the known-valid `uuid` column to `text` instead never errors,
regardless of evaluation order.

A no-op on any non-Postgres connection (local/dev/CI-by-default all use
SQLite per .env.example) — RLS does not exist there, so there's nothing to
apply, and running raw `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` against
SQLite would simply error.
"""

from django.db import migrations

TABLE = "subscriptions_subscription"

ENABLE_SQL = f"""
ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {TABLE} FORCE ROW LEVEL SECURITY;

CREATE POLICY {TABLE}_tenant_select ON {TABLE}
    FOR SELECT
    USING (
        current_setting('app.current_org_id', true) = '*'
        OR organization_id::text = current_setting('app.current_org_id', true)
    );

CREATE POLICY {TABLE}_write_insert ON {TABLE}
    FOR INSERT WITH CHECK (true);

CREATE POLICY {TABLE}_write_update ON {TABLE}
    FOR UPDATE USING (true) WITH CHECK (true);

CREATE POLICY {TABLE}_write_delete ON {TABLE}
    FOR DELETE USING (true);
"""

DISABLE_SQL = f"""
DROP POLICY IF EXISTS {TABLE}_tenant_select ON {TABLE};
DROP POLICY IF EXISTS {TABLE}_write_insert ON {TABLE};
DROP POLICY IF EXISTS {TABLE}_write_update ON {TABLE};
DROP POLICY IF EXISTS {TABLE}_write_delete ON {TABLE};
ALTER TABLE {TABLE} NO FORCE ROW LEVEL SECURITY;
ALTER TABLE {TABLE} DISABLE ROW LEVEL SECURITY;
"""


def enable_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(ENABLE_SQL)


def disable_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(DISABLE_SQL)


class Migration(migrations.Migration):
    dependencies = [("subscriptions", "0001_initial")]

    operations = [migrations.RunPython(enable_rls, disable_rls)]
