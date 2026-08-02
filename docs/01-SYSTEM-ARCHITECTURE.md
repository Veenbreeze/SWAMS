# SWAMS — Smart Workforce Attendance Management System
## Software Architecture Document (SAD)

Version 1.0 — Draft for approval
Status: **Pending sign-off before Phase 2 implementation begins**

---

## 1. Purpose and Scope

SWAMS is a multi-tenant SaaS platform that lets organizations manage employee
attendance using GPS/geofence verification from a mobile app, with a web
back-office for organization admins and a separate control plane for the
platform owner (Super Admin).

This document defines the system architecture, the tenancy model, the
security model, and the deployment topology. It is the reference all three
applications (Super Admin Web, Organization Admin Web, Employee Mobile) and
the shared backend are built against.

---

## 2. Architectural Style

**Backend:** Modular monolith, Django + DRF, organized as bounded-context
apps communicating in-process (no premature microservices — a single
Postgres-backed Django service scales to "thousands of organizations" with
correct indexing, caching, and read replicas long before microservices are
justified). Each Django app is internally layered using Clean
Architecture / Hexagonal principles so business logic is not trapped in
views or models, which keeps the door open to extracting a service later
(e.g., attendance/geofencing) without a rewrite.

**Frontends:** Two independent SPAs (Super Admin, Organization Admin) built
from a shared component/design-system library, plus one Expo mobile app.
All three talk to the same DRF API through a versioned `/api/v1/` contract.

**Communication:** Synchronous REST over HTTPS for all client-server calls.
Asynchronous work (notifications, report generation, PDF/Excel export,
subscription-expiry checks) runs on Celery + Redis so request latency for
check-in/check-out stays low.

### 2.1 Clean Architecture inside a Django app

Each domain app (`employees`, `attendance`, `leave`, ...) is split into four
layers so business rules don't leak into Django/DRF plumbing:

```
apps/attendance/
  domain/           # Pure Python: entities, value objects, business rules
    entities.py     #   e.g. GeofenceCheck, AttendanceStatus calculation
    exceptions.py   #   OutsideGeofenceError, PoorGpsAccuracyError, ...
  application/       # Use cases / services — orchestrate domain + repos
    services.py      #   CheckInService, CheckOutService
    interfaces.py     #  Repository/Port ABCs
  infrastructure/     # Django ORM models, repositories, external services
    models.py
    repositories.py   #  implements ports from application/interfaces.py
  interfaces/          # HTTP boundary
    serializers.py
    views.py
    urls.py
    permissions.py
  tests/
```

Rule of dependency: `interfaces` → `application` → `domain`.
`infrastructure` implements ports defined in `application`, and is injected
at the view layer (simple constructor/DI, no framework needed). Domain code
never imports Django. This is what lets geofence math, late/absent
calculation, and leave-balance logic be unit-tested with zero DB access.

---

## 3. The Three Applications

| App | Users | Hosting | Auth |
|---|---|---|---|
| Super Admin Web | Platform owner/staff | Render (static) | JWT, `role=SUPER_ADMIN`, no `organization_id` |
| Organization Admin Web | Org owner/HR/Admin/Manager | Render (static) | JWT, scoped to one `organization_id` |
| Employee Mobile (Expo) | Employees | App stores / OTA (EAS Update) | JWT, scoped to one `organization_id` |

All three are pure API clients of one Django backend — no app has direct DB
access.

---

## 4. Multi-Tenant Architecture

**Model:** Shared database, shared schema, discriminator column
(`organization_id`) — the standard, most cost-effective model for a SaaS
serving many small/medium organizations on Postgres, and the one explicitly
requested. Row-Level Security (RLS) is layered on top in Postgres as
defense-in-depth (see §6.3); Django-level enforcement is the primary
control since the API is the only client of the DB.

### 4.1 Tenant resolution

1. Client authenticates → JWT access token carries `organization_id`,
   `user_id`, `role` as claims (Super Admin tokens carry `organization_id:
   null`).
2. `TenantMiddleware` runs after JWT auth, reads the claim, and binds it to
   a request-scoped context (`contextvars`, not thread-locals, so it is
   safe under async/Celery workers too).
3. A custom `TenantAwareManager`/base `TenantModel` auto-filters every
   queryset by the bound `organization_id` — a developer would have to
   deliberately opt out (`.all_tenants()`) to bypass it, rather than
   deliberately opt in, so a forgotten `.filter(organization=...)` fails
   safe.
4. Every write path re-validates that any foreign key referenced in the
   payload (branch_id, department_id, employee_id, ...) belongs to the
   caller's `organization_id` before saving — prevents cross-tenant IDOR
   even if a client sends another org's numeric ID.
5. Super Admin endpoints live under a separate URL namespace
   (`/api/v1/platform/...`) and explicitly require `role=SUPER_ADMIN`; they
   are the only endpoints allowed to query across organizations, and only
   in read/management form (create org, suspend org, view aggregate
   stats) — never employee attendance data.

### 4.2 Why not schema-per-tenant / DB-per-tenant

Rejected for v1: operationally heavier (migrations run N times), and not
needed until a customer requires physical data isolation (some enterprise
or government tenants might, later — the shared-schema + RLS design can
migrate a single large tenant out to its own schema without an application
rewrite, so this is not a dead end).

---

## 5. Role-Based Access Control (RBAC)

Four fixed roles (not a fully dynamic permission-builder in v1 — enterprise
customers rarely need custom roles for attendance software, and a fixed
enum keeps authorization logic auditable):

| Role | Tenant-scoped? | Notes |
|---|---|---|
| `SUPER_ADMIN` | No (platform-wide) | Not tied to any `organization_id` |
| `ORG_ADMIN` | Yes | One per org typically, can create more |
| `MANAGER` | Yes | Scoped further to assigned department(s)/employees |
| `EMPLOYEE` | Yes | Self-service only |

Enforcement layers (all required, not either/or):

1. **Authentication** — `IsAuthenticated`.
2. **Role check** — DRF permission class per view/action,
   e.g. `IsOrgAdmin`, `IsManagerOrAbove`, `IsSelfOrAdmin`.
2. **Object-level check** — a permission class or service-layer guard
   confirms the target object's `organization_id` matches the caller's,
   and for Managers, that the target employee is within their assigned
   scope.
3. **Field-level check** — serializers expose different writable fields
   per role (e.g., Employee's `ProfileUpdateSerializer` excludes
   `role`, `department`, `branch`, `employee_number`, `organization`).

No permission decision is ever made from a value the client sent (e.g. a
`role` field in a request body is always ignored/stripped server-side for
self-service endpoints).

---

## 6. Security Architecture

### 6.1 Authentication

- Login payload: `organization_code + identifier(email|employee_number) +
  password`. Organization code is resolved to `organization_id` first
  (also throttled/rate-limited — this triple is effectively the account
  identifier and must be brute-force-resistant).
- Password hashing: Django's default PBKDF2 (upgradeable to Argon2 via
  `PASSWORD_HASHERS` without data migration — Django rehashes on next
  successful login).
- JWT via `djangorestframework-simplejwt`: short-lived access token
  (~15 min), rotating refresh token (~7–30 days) stored **only** in
  Expo SecureStore (mobile) / httpOnly cookie or in-memory (web — never
  `localStorage`, to reduce XSS token theft).
- Refresh token rotation + reuse detection: each refresh issues a new
  refresh token and blacklists the old one; if a blacklisted token is
  replayed, all sessions for that user are revoked and a security event is
  logged (classic stolen-token detection).
- Account lockout: N consecutive failed attempts (configurable, default 5)
  locks the account for a cooldown window; every attempt (success or
  failure) is written to `LoginHistory`.
- "Logout of all devices" revokes all outstanding refresh tokens for the
  user.
- First-login flow for employees: Admin-created accounts are issued with
  `must_change_password=True` and a temporary password; **every**
  authenticated endpoint except `change-password` is blocked until the
  flag is cleared (enforced server-side by middleware/permission, not by
  the mobile app choosing to show a screen).

### 6.2 Authorization

Covered in §5. Key rule restated: **the backend is the only trust
boundary.** Frontend route guards and hidden buttons are UX, not security.

### 6.3 Data isolation defense-in-depth

1. Tenant-scoped ORM manager (primary control, §4.1).
2. Object-level permission checks in views/services (secondary control).
3. Postgres Row-Level Security policies keyed on a session variable set by
   the connection at request start (`SET app.current_org_id = ...`) as a
   last-resort control if application code ever forgets a filter.
4. Every cross-tenant access attempt (403 due to org mismatch) is logged
   as a `SecurityEvent`, not silently dropped — repeated attempts from one
   account/IP are a signal worth alerting on.

### 6.4 API security

- HTTPS enforced (`SECURE_SSL_REDIRECT`), HSTS, `X-Content-Type-Options`,
  `X-Frame-Options`, `Referrer-Policy` via `django-security`/manual
  middleware.
- CORS: explicit allow-list of the two web app origins per environment;
  no wildcard.
- CSRF: not applicable to token-authenticated API calls (no session
  cookies used for API auth); CSRF protection stays on for the Django
  admin.
- Rate limiting: DRF throttling per-IP and per-user, tighter limits on
  `/auth/login`, `/auth/password-reset`, `/attendance/check-in`.
- Input validation: DRF serializers validate every field server-side
  (type, range, required); GPS coordinates bounds-checked
  (-90..90 / -180..180), accuracy must be a positive number, timestamps
  can't be in the future beyond clock-skew tolerance.
- SQL injection: ORM-only, no raw SQL string interpolation; if raw SQL is
  ever needed (reporting), parameterized queries only.
- XSS: DRF returns JSON only (no template rendering of user input);
  frontend uses React's default escaping and never `dangerouslySetInnerHTML`
  with user content.

### 6.5 File security

- Uploads (profile pictures, org logos) go straight to Supabase Storage via
  signed upload URLs issued by the backend — the Django server itself never
  buffers untrusted files into request memory beyond a size-checked stream.
- Server-side validation before issuing a signed URL / on webhook
  confirmation: allow-listed MIME types (`image/jpeg`, `image/png`,
  `image/webp`), max size (e.g. 5 MB for photos, 2 MB for logos), and
  image re-encoding (Pillow) to strip EXIF/GPS metadata and neutralize
  polyglot files.
- Filenames are never client-supplied — server generates
  `uuid4 + extension`; storage path is namespaced by
  `organization_id/employee_id/...` and bucket policies deny cross-tenant
  reads.

### 6.6 Anti location-spoofing

Attendance requests are DENIED (not just flagged) when the client reports
`isMockLocation=true` (Android) or when the request omits required GPS
metadata. Because a spoofed client can lie, this is one layer among several:

- Reported GPS accuracy must be ≤ `branch.gps_accuracy_limit`, else denied
  with the "move to an open area" message.
- Distance-from-branch (Haversine) must be ≤ `branch.radius`.
- Server-side plausibility check: if two consecutive attendance events
  from the same device imply impossible travel speed between two branch
  locations, flag as a `SecurityEvent` for admin review rather than
  silently accepting.
- Device binding: each mobile install registers a `device_id`
  (Expo `installationId` + device model/OS); check-in requests are
  compared against previously seen devices for that employee, and a new
  device triggers a notification to the employee and (optionally) the org
  admin.
- All of the above are recorded on the `Attendance` row itself
  (`latitude`, `longitude`, `accuracy`, `device_id`, `is_mock_location`,
  `timestamp`) so disputes are auditable after the fact — this is
  detection and evidence, not a claim of cryptographic proof of location,
  which is not achievable from a stock consumer GPS.

### 6.7 Audit logging

`AuditLog` is append-only: no `UPDATE`/`DELETE` permission is granted to
the application DB role on that table (enforced at the Postgres grant
level, not just Django); a scheduled archival job may move rows older than
the retention period to cold storage, but normal app code cannot delete.
Every state-changing endpoint writes exactly one audit entry per action via
a shared service (`AuditLogger.record(actor, action, target, request)`) so
logging isn't left to be remembered ad hoc per view.

---

## 7. Attendance / Geofencing Engine (core domain logic)

Pure-domain, framework-free, unit-testable:

```
GeofenceValidator.evaluate(
    employee_location: GpsReading,
    branch: BranchLocation,
) -> GeofenceResult
```

Decision table:

| distance ≤ radius | accuracy ≤ limit | mock location | Result |
|---|---|---|---|
| yes | yes | no | ALLOW |
| yes | no | any | DENY — "Unable to verify your location..." |
| no | any | any | DENY — "You are outside the authorized workplace location." |
| any | any | yes | DENY — flagged as SecurityEvent |

Distance uses the Haversine formula against the branch's stored
lat/lng/radius. `AttendanceStatusCalculator` then derives
`PRESENT / LATE / EARLY_DEPARTURE / ABSENT / OVERTIME` from the org's
`AttendanceRule` (working days, start/end time, late threshold) and the
employee's assigned `Shift`, independent of the geofence check — a
late-but-inside-geofence check-in is allowed and simply marked `LATE`.

---

## 8. Notification Architecture

- **In-app:** `Notification` rows, polled/paginated via
  `GET /api/v1/notifications`, marked read individually or in bulk.
- **Push:** Expo Push Notification service; device push tokens stored per
  employee, sent via a Celery task so check-in latency isn't blocked on a
  push provider round-trip.
- **Email:** Django email backend (SMTP via env-configured provider —
  e.g. SendGrid/Mailgun/SES), used for password reset, admin-level
  security alerts, and org-level digest reports.
- **SMS-ready:** an `SmsProvider` interface with a no-op/logging
  implementation in v1 and a documented contract so a Tanzanian SMS
  gateway (e.g. Beem Africa, Africa's Talking) can be plugged in later
  without touching call sites.

All three channels are triggered from one `NotificationDispatcher` service
so business code calls `notify(event, recipients)` once, not three times.

---

## 9. Deployment Architecture

```
                    ┌─────────────────────────┐
                    │        Render           │
                    │  ┌───────────────────┐  │
   Browser ───────▶ │  │ org-admin-web     │  │
   Browser ───────▶ │  │ super-admin-web   │  │  (static sites)
                    │  └───────────────────┘  │
                    │  ┌───────────────────┐  │
   Expo App ──────▶ │  │ swams-api (Django │  │
   (mobile)         │  │ + Gunicorn)       │  │──▶ Redis (Render) — cache, Celery broker
                    │  │ swams-worker      │  │
                    │  │ (Celery)          │  │
                    │  │ swams-beat        │  │
                    │  └───────────────────┘  │
                    └───────────┬─────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │        Supabase         │
                    │  Postgres (primary DB)  │
                    │  Storage (files/logos)  │
                    └─────────────────────────┘
```

- Backend: Render Web Service, Gunicorn (`gunicorn core.wsgi`), health
  check endpoint `/api/v1/health/`, `DATABASE_URL` pointed at Supabase
  Postgres (connection pooled via Supabase's PgBouncer / `pgbouncer=true`
  mode to survive Render's short-lived dynos + Django's per-request
  connections).
- Background: a separate Render Worker service for Celery, and a Render
  Cron/worker for Celery Beat (subscription-expiry checks, daily/weekly
  report pre-generation, stale-session cleanup).
- Frontends: two separate Render Static Sites built with Vite
  (`VITE_API_BASE_URL` injected per environment).
- Database migrations run as a Render **pre-deploy / release command**
  (`python manage.py migrate`), never manually against production.
- Environments: `local` → `staging` → `production`, each with its own
  Supabase project and its own `.env` (see §31 in the original brief) —
  no environment shares a database.

---

## 10. Performance & Scalability

- Indexing strategy in §16 of the ERD doc — every hot query path
  (`organization_id`, `employee_id`, `created_at`/date range) is covered
  by a composite index.
- Pagination on every list endpoint (cursor-based for `Attendance`, which
  grows unbounded; page-number for small admin lists).
- `select_related`/`prefetch_related` mandated in code review for any
  serializer touching FKs, to avoid N+1 (checked by `django-silk`/
  `nplusone` in dev, not just convention).
- Redis caching for read-heavy, slow-changing data: branch geofence
  config, attendance-rule config, org subscription status — invalidated
  on write.
- Heavy work (monthly report generation, PDF/Excel export, bulk
  notification fan-out) is Celery-async; the API returns a job handle /
  signed download URL once ready rather than blocking.
- Table partitioning path: `Attendance` and `AuditLog` are designed so
  that, when volume warrants (millions of rows), Postgres native
  partitioning by month can be introduced without an application-level
  schema change (partition key = `created_at`, already the leading index
  column).

---

## 11. Internationalization

English + Kiswahili from day one: Django `USER_LANGUAGE` / `i18n` on
error messages and email/notification templates; React uses `i18next`;
Expo uses `i18n-js`/`expo-localization`. All user-facing strings (incl.
geofence denial messages) are translation keys, not hardcoded English, from
the first commit — retrofitting i18n later is far costlier than building
it in.

---

## 12. Decisions (resolved)

1. **Password hasher:** Argon2 from day one (`argon2-cffi`, set as the
   first entry in `PASSWORD_HASHERS`).
2. **Subscription billing:** admin-managed status only for v1 — no
   payment gateway integration in Phase 8. `Subscription`/`SubscriptionPlan`
   are still modeled so a billing provider can be added later without a
   schema migration.
3. **iOS mock-location:** accepted limitation for v1. Distance + accuracy
   + device-binding remain the primary control on iOS (no reliable
   `isMockLocation` equivalent exists); documented as a known limitation,
   not a launch blocker.
4. **Data residency:** no specific requirement — use the default/nearest
   Supabase region.

---
