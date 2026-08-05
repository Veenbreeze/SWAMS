# 06 — Runbook

Operational reference for SWAMS once code is ready to ship: first deploy,
rollback, secret rotation, and onboarding a new organization. Written
against the actual [`render.yaml`](../render.yaml) blueprint and
[`mobile/eas.json`](../mobile/eas.json) in this repo — if either changes,
update this doc alongside it.

See [`docs/01-SYSTEM-ARCHITECTURE.md`](01-SYSTEM-ARCHITECTURE.md) §9 for
the deployment topology diagram this runbook operates against.

---

## 1. First deploy (new environment)

Do this once per environment (`staging`, `production`) — each gets its own
Supabase project and its own set of Render services. Never point a staging
environment at a production database or vice versa.

### 1.1 Provision Supabase

1. Create a new Supabase project for this environment.
2. Copy the Postgres connection string (session-mode pooler, not
   transaction-mode — Django needs a stable session for `SET
   app.current_org_id`, see Architecture §6.3) into `DATABASE_URL`.
3. Create the three Storage buckets used by `backend/storage/supabase_client.py`:
   `profile-pictures`, `org-logos`, `documents`. Set bucket policies to deny
   cross-tenant reads (paths are namespaced `organization_id/...`).
4. Copy the project's `SUPABASE_URL` and a **service-role** key (not the
   anon key — the backend needs to issue signed upload/download URLs
   server-side) into `SUPABASE_URL` / `SUPABASE_SERVICE_KEY`.

### 1.2 Provision Render

1. Push `render.yaml` to the branch Render is watching, then create a new
   Blueprint instance from it in the Render dashboard. This provisions in
   one shot: `swams-api`, `swams-worker`, `swams-beat`, `swams-redis`,
   `swams-org-admin`, `swams-super-admin`.
2. Fill in every `sync: false` var in the `swams-shared` group (Render
   dashboard → the env var group, not per-service — all three Python
   services read from it):
   - `DJANGO_SECRET_KEY` — generate a fresh one per environment (`python -c
     "import secrets; print(secrets.token_urlsafe(50))"`). **Never** reuse
     the value from another environment or from `.env.example`.
   - `DJANGO_ALLOWED_HOSTS` — the `swams-api` Render hostname (or custom
     domain once attached).
   - `CORS_ALLOWED_ORIGINS` — the exact origins of `swams-org-admin` and
     `swams-super-admin` for this environment. No wildcards (Architecture
     §6.4).
   - `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` — from step 1.1.
   - `EMAIL_HOST` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` — your SMTP
     provider (SendGrid/Mailgun/SES). Until this is set, password-reset and
     notification emails silently no-op against the console backend — fine
     for a first smoke test, not for real use.
   - `SMS_API_KEY` — leave blank until an SMS gateway is actually
     integrated (`apps/notifications/services/sms.py` is a documented
     no-op without it; nothing breaks by leaving it unset).
   - `FRONTEND_PASSWORD_RESET_URL` — the org-admin app's `/reset-password`
     route, e.g. `https://<swams-org-admin-host>/reset-password`.
3. Set `VITE_API_BASE_URL` on both `swams-org-admin` and `swams-super-admin`
   to the `swams-api` service's public URL + `/api/v1`.
4. Trigger the first deploy. Render runs `preDeployCommand: python
   manage.py migrate` automatically before `swams-api` goes live — never
   run migrations by hand against a live environment outside this step.
5. Confirm `swams-api`'s health check (`/api/v1/health/`) is green, then
   create the first Super Admin (there is no self-service signup for this
   role — see 1.3).

### 1.3 Bootstrap the first Super Admin

No UI creates the very first Super Admin (every other one is created by an
existing Super Admin through the platform app). Run once, against the
live environment, via Render's shell for `swams-api`:

```bash
python manage.py shell -c "
from apps.authentication.models import UserAccount, Role
UserAccount.objects.create_superuser(
    email='<real-email>', password='<strong-temporary-password>',
)
"
```

`create_superuser` sets `role=SUPER_ADMIN`, `organization=None`,
`is_staff=True`. Log in at `swams-super-admin`'s `/login` with no
organization code, then immediately change the password from Settings —
this account was created with a password typed into a shell, treat it as
compromised until rotated.

### 1.4 Mobile (EAS, not Render)

The Expo app is not part of the Render blueprint — it ships through EAS.

```bash
cd mobile
eas build --profile production --platform all   # or staging, per environment
eas submit --profile production                  # after store review setup
```

Set `EXPO_PUBLIC_API_BASE_URL` for the target environment in `eas.json`'s
`build.<profile>.env` (or an EAS environment variable) before building —
it's inlined into the bundle at build time, so a wrong value means
rebuilding, not just reconfiguring.

---

## 2. Rollback

**Backend (`swams-api`, `swams-worker`, `swams-beat`):** Render keeps
previous deploys. In the dashboard, open the service → **Deploys** → pick
the last known-good deploy → **Rollback**. Do this for all three Python
services together — they must run the same code revision, since
`swams-beat` schedules tasks that `swams-worker` executes and both share
`core.settings.production`.

**Migrations:** Render's `preDeployCommand` only runs `migrate` forward.
Rolling back a deploy does **not** reverse a migration that already ran.
If the bad deploy included a migration:

1. Roll back the three Python services first (previous code, current —
   already-migrated — schema).
2. Only reverse the migration by hand (`python manage.py migrate
   <app> <previous_migration_name>`) if the previous code revision is
   actually incompatible with the new schema — check the migration's
   `reversible` state and whether it dropped/renamed a column before
   doing this. Prefer rolling forward with a fix over reversing a
   migration against a live database.

**Frontends (`swams-org-admin`, `swams-super-admin`):** same Deploys →
Rollback flow; these are static builds, so this is safe and instant with
no data implications.

**Mobile:** you cannot "roll back" an app already on a user's device.
Use `eas update` (if the project has an EAS Update channel configured) to
push a JS-only revert immediately, or expedite a new store build for a
native-code issue. This is why `EXPO_PUBLIC_API_BASE_URL`-breaking changes
and native module changes deserve extra pre-release testing — they're the
two classes of mobile bug that can't be hotfixed instantly.

---

## 3. Rotating secrets

Every secret below lives in exactly one place — the `swams-shared` env var
group on Render (Python services) or the equivalent EAS/env var for
mobile. Rotate by updating the value there and redeploying; never commit a
new value anywhere in the repo.

| Secret | Rotate by | Blast radius while rotating |
|---|---|---|
| `DJANGO_SECRET_KEY` | Generate a new value, update the env var group, redeploy `swams-api`+`swams-worker`+`swams-beat` together | Invalidates all outstanding JWTs (users are logged out) and any in-flight password-reset links. Plan for a maintenance window or off-peak deploy. |
| `DATABASE_URL` | Rotate the Postgres password in Supabase's dashboard, update the env var, redeploy the three Python services | Any request mid-flight during the redeploy window fails and retries; no data risk. |
| `SUPABASE_SERVICE_KEY` | Roll the service-role key in Supabase project settings, update the env var, redeploy | Signed URLs already issued keep working until they expire; new ones use the new key immediately after redeploy. |
| `EMAIL_HOST_PASSWORD` / SMTP creds | Rotate with your email provider, update the env var, redeploy | Emails queued during the gap retry via Celery's normal retry policy — nothing is lost, just delayed. |
| `SMS_API_KEY` | Same pattern, once a real gateway is wired in (currently a documented no-op) | None — no gateway is live yet. |
| A compromised Super Admin or Org Admin password | That user (or another Super Admin, for a locked-out account) uses `POST /auth/change-password` or the password-reset flow — no redeploy needed | Scoped to that one account. Check `LoginHistory`/`SecurityEvent` for the account afterward. |
| A suspected leaked refresh token | `POST /auth/logout-all` for that user (or have a Super Admin do it), or wait for the built-in reuse-detection to trip on replay | Scoped to that one account's active sessions. |

**Never** rotate `DJANGO_SECRET_KEY` by editing `.env.example` or any
committed file — it has no real value there by design (`insecure-dev-key-do-not-use-in-production`
is a local-only fallback, and `core/settings/production.py` refuses to
boot without a real `DJANGO_SECRET_KEY` env var, per its own comment).

---

## 4. Onboarding a new organization (Super Admin walkthrough)

1. Log in to `swams-super-admin` as a Super Admin.
2. **Subscriptions → Subscription Plans**: confirm a plan exists for this
   organization's tier (create one via **New plan** if not — code, name,
   monthly price, max employees/branches, grace period days).
3. **Organizations → New organization** *(once that page is built out past
   its current stub — until then, use the API directly:
   `POST /api/v1/platform/organizations` with `code`, `name`,
   `registration_number`, `email`, `phone`, `admin_email`)*. This creates
   the organization **and** bootstraps its first Org Admin in one call,
   returning a `temporary_password` for that admin — copy it now, it is
   not shown again.
4. **Subscriptions → Subscription Plans → Assign subscription**: pick the
   new organization, the plan from step 2, and a start/expiry date. This
   is what the daily expiry-sweep (`apps.subscriptions.tasks.check_subscription_expiries`)
   tracks — an organization with no subscription row is silently skipped
   by that job, so don't leave this step out.
5. Send the new Org Admin their `code` (organization login code) and
   `temporary_password` out-of-band (not email, since email delivery for
   this environment may not be configured yet — see 1.2). They sign in at
   `swams-org-admin`'s login with all three: organization code, their
   email, the temporary password. `must_change_password` forces a
   password change before anything else in the app is usable.
6. The Org Admin then creates branches, departments, and employees for
   their own organization — none of that is a Super Admin responsibility
   past this point.
7. Confirm the organization shows up correctly: **Dashboard** shows the
   new organization in `total_organizations`/`new_organizations_last_30_days`,
   and **Expiry Monitor** shows nothing for it (since its subscription was
   just assigned with a real expiry date, it won't appear until inside the
   30-day window).

---

## 5. Quick reference

- Health check: `GET https://<swams-api-host>/api/v1/health/` — should
  return `200` with no auth required. This is what Render's own health
  check hits; use it yourself first when diagnosing "is the API even up."
- Logs: Render dashboard → service → **Logs**, for all five backend
  services independently. `swams-beat`'s logs are the first place to check
  if subscription-expiry warnings/suspensions stop firing — confirm it's
  actually running (Render worker services don't have a health check
  endpoint the way `swams-api` does, so "deployed" isn't the same as
  "still running").
- Database console: use Supabase's SQL editor for read-only investigation.
  Never run `UPDATE`/`DELETE` there against tenant-scoped tables — the
  Supabase SQL editor typically connects as the Postgres superuser/owner,
  which **bypasses Row-Level Security** (Architecture §6.3's last line of
  defense doesn't apply to that connection), so a mistyped `WHERE` clause
  there has no RLS safety net the app itself relies on.

---

## 6. Check-in endpoint load-test notes

`POST /api/v1/attendance/check-in` is the highest-traffic, most
latency-sensitive path (roadmap Phase 9) — twice daily per employee,
clustered at shift start/end. It was load-tested locally against real
Postgres (a throwaway, non-superuser-owned container, matching every RLS
test in this repo) with 200 distinct employees checking in against one
branch, using pre-minted JWTs so the test isolates check-in itself rather
than also exercising `/auth/login`'s separate, tighter per-IP throttle
(10/min — a fleet of phones on distinct IPs wouldn't trip it the way N
threads from one test machine would).

**Findings:**

- **Single-request baseline: ~100–150 ms.** One check-in, no concurrency,
  is healthy — geofence math, attendance-status calculation, the DB write,
  and (no-op stub) notification dispatch together cost well under 200 ms.
- **10 concurrent employees checking in at once: p50 ≈ 1.3 s, p95 ≈ 3.8 s,
  0 failures.** A real shift-start burst at this scale is handled
  correctly, just noticeably slower than the single-request baseline.
- **50 concurrent: severe degradation (p50 ≈ 7 s) and some connection-level
  failures.** Root-caused to Django's development server
  (`manage.py runserver`) itself, not application code: it's a
  single-process, GIL-bound, small-listen-backlog server — exactly why
  `render.yaml` runs `gunicorn core.wsgi:application` in every real
  environment (pre-forked worker processes, no GIL contention across
  workers, a real listen backlog). **Gunicorn does not run on Windows**
  (`fcntl` is POSIX-only), so this repo's load test could not be re-run
  against it locally — re-run the same script against a real `swams-api`
  staging deploy (or any Linux box) before trusting the 50-concurrent
  numbers; the 10-concurrent numbers and the single-request baseline are
  the trustworthy signal from this pass.
- No correctness issues surfaced at any concurrency level: no cross-tenant
  data observed, no duplicate check-ins allowed through, no 500s — every
  failure was a client-side connection refusal from the dev server's
  backlog, not an application error.
- A **Windows-specific gotcha**, unrelated to the app, worth remembering
  for any future local load test on this platform: hitting `localhost`
  added a consistent, spurious ~2 s per request (an IPv6-then-IPv4
  DNS-resolution quirk) versus hitting `127.0.0.1` directly. Always use
  the literal IP for local load tests.
