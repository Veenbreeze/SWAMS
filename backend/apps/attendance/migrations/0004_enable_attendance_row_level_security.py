"""Postgres RLS for the `Attendance` table, added alongside
0002_enable_row_level_security.py rather than folded into it since this
migration depends on 0003_attendance (the model didn't exist yet when
0002 ran). Same pattern/rationale — see
apps/subscriptions/migrations/0002_enable_row_level_security.py and
apps/audit_logs/migrations/0002_enable_row_level_security.py.
"""

from django.db import migrations

TABLE = "attendance_attendance"

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
    dependencies = [("attendance", "0003_attendance")]

    operations = [migrations.RunPython(enable_rls, disable_rls)]
