"""Postgres RLS as defense-in-depth for this app's tenant-scoped table —
see apps/subscriptions/migrations/0002_enable_row_level_security.py for
the full rationale and apps/audit_logs/migrations/0002_enable_row_level_security.py
for why the SELECT policy compares `organization_id::text` rather than
casting the session var to `uuid`.
"""

from django.db import migrations

TABLES = ["feedback_recommendation"]


def _enable_sql(table):
    return f"""
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {table} FORCE ROW LEVEL SECURITY;

CREATE POLICY {table}_tenant_select ON {table}
    FOR SELECT
    USING (
        current_setting('app.current_org_id', true) = '*'
        OR organization_id::text = current_setting('app.current_org_id', true)
    );

CREATE POLICY {table}_write_insert ON {table}
    FOR INSERT WITH CHECK (true);

CREATE POLICY {table}_write_update ON {table}
    FOR UPDATE USING (true) WITH CHECK (true);

CREATE POLICY {table}_write_delete ON {table}
    FOR DELETE USING (true);
"""


def _disable_sql(table):
    return f"""
DROP POLICY IF EXISTS {table}_tenant_select ON {table};
DROP POLICY IF EXISTS {table}_write_insert ON {table};
DROP POLICY IF EXISTS {table}_write_update ON {table};
DROP POLICY IF EXISTS {table}_write_delete ON {table};
ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;
ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;
"""


def enable_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        for table in TABLES:
            cursor.execute(_enable_sql(table))


def disable_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        for table in TABLES:
            cursor.execute(_disable_sql(table))


class Migration(migrations.Migration):
    dependencies = [("feedback", "0001_initial")]

    operations = [migrations.RunPython(enable_rls, disable_rls)]
