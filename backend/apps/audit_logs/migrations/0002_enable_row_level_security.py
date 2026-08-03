"""Postgres RLS as defense-in-depth — see
apps/subscriptions/migrations/0002_enable_row_level_security.py for the
full rationale (SELECT-only restriction, permissive writes, `WILDCARD`
sentinel for Super Admin platform-wide reads, Postgres-only).

`organization_id IS NULL` rows (platform-level actions with no single
owning tenant, e.g. Super Admin creating an organization) are visible only
under the `WILDCARD` session — a tenant-bound session has no legitimate
reason to see platform-level audit rows, so unlike the plain-org branch
this isn't opened up to everyone by default. `NULL::text = current_setting(...)`
is itself NULL (not true) for both a concrete tenant session and the
unbound/reset empty-string session, so this falls out of the same
comparison as the concrete-org case rather than needing its own clause.

Compares `organization_id::text` against the session var rather than
casting the session var to `uuid` — confirmed against a real Postgres
instance that the `OR` is NOT safely short-circuited here, so casting the
`'*'` sentinel itself to `uuid` raised `invalid input syntax for type uuid`
on every Super Admin (WILDCARD) read of an org-scoped row. Casting the
known-valid `uuid` column to `text` instead never errors.
"""

from django.db import migrations

TABLE = "audit_logs_auditlog"

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
    dependencies = [("audit_logs", "0001_initial")]

    operations = [migrations.RunPython(enable_rls, disable_rls)]
