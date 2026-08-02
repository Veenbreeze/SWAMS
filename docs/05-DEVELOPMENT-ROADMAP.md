# SWAMS — Development Roadmap

Phased per the brief's §33, expanded into concrete deliverables and
acceptance criteria so each phase has a clear "done" line before the next
starts. Sequencing reflects real dependencies (e.g., attendance cannot be
built before tenancy + employees exist).

---

## Phase 1 — Project Foundation

**Goal:** every project boots, talks to a real (Supabase) Postgres, and
deploys an empty "hello" page/endpoint to Render.

- Initialize git repo; commit this `docs/` set.
- `backend/`: Django project + DRF installed, `core/settings` split
  (base/local/staging/production), `.env` loading via `django-environ`,
  Supabase Postgres connection verified locally, `/health` endpoint.
- `frontend-org-admin/` and `frontend-super-admin/`: Vite + React (JS) +
  Tailwind + shadcn/ui scaffolded, one placeholder route each, Axios
  client stub.
- `mobile/`: Expo app scaffolded, splash screen, Expo Go run verified on a
  physical device.
- Supabase project(s) created for `local`/`staging`; Storage buckets
  created (`profile-pictures`, `org-logos`, `documents`) with bucket
  policies stubbed.
- Render Blueprint (`render.yaml`) draft: web service + two static sites +
  worker + Redis, wired to staging Supabase.
- CI skeleton: lint + test job on push (GitHub Actions or equivalent).

**Acceptance:** `docker-compose up`/local run works for backend; both web
apps build (`vite build`) cleanly; Expo app runs in Expo Go; a trivial
`/health` deploy succeeds on Render staging.

---

## Phase 2 — Authentication & RBAC Core

**Goal:** login works end-to-end for all four roles against real JWTs,
with the security controls from Architecture §6.1 in place.

- `UserAccount` model (custom `AUTH_USER_MODEL`), password hashing
  (confirm Argon2 vs PBKDF2 — open decision in Architecture §12).
- `simplejwt` integration: access/refresh issuance, rotation, blacklist
  app enabled.
- Login endpoint with `organization_code + identifier + password`,
  org-code resolution, failed-attempt counter + lockout.
- `LoginHistory`, `Device`, `RefreshToken` models wired into
  login/refresh/logout flows.
- `must_change_password` enforcement middleware/permission.
- Change-password, password-reset request/confirm endpoints.
- RBAC permission classes (`IsSuperAdmin`, `IsOrgAdmin`,
  `IsManagerOrAbove`, `IsSelf`) + `TenantMiddleware` binding
  `organization_id` from JWT claims.
- Frontend: Login pages (both web apps) wired to real API; token storage
  per Architecture §6.1 (no `localStorage` for tokens); force-change-
  password screen.
- Mobile: Login screen, SecureStore token storage, force-change-password
  screen.
- Tests: login success/failure/lockout, token refresh + reuse detection,
  role permission matrix, tenant-isolation regression test (org A cannot
  fetch org B's user via any endpoint that exists so far).

**Acceptance:** all four roles can log in; a token from org A is rejected
on any org-B-scoped resource with `CROSS_TENANT_ACCESS`; reused refresh
token revokes the session; test suite covers the permission matrix.

---

## Phase 3 — Multi-Tenancy & Organization Management

**Goal:** Super Admin can create/manage organizations; org data isolation
is provable, not assumed.

- `Organization`, `SubscriptionPlan`, `Subscription` models.
- Super Admin endpoints: create org (+ bootstraps first Org Admin user),
  edit, suspend, activate, list, detail.
- `TenantAwareManager`/base `TenantModel` implemented and applied to every
  subsequent tenant-scoped model going forward.
- Row-Level Security policies added for tables that exist so far
  (Architecture §6.3 / ERD §5).
- `AuditLog` service (`AuditLogger.record`) wired to org create/edit/
  suspend/activate.
- Super Admin Web: Organization list, create, detail, suspend/activate
  UI; platform dashboard skeleton (counts only, real charts in Phase 6).
- Tests: org suspension blocks login for that org's users; RLS policy
  test (raw SQL as a different `app.current_org_id` cannot read another
  org's rows even bypassing the ORM manager).

**Acceptance:** Super Admin can fully manage the org lifecycle; a
suspended org's employees cannot authenticate; isolation is verified by
an automated test that tries to break it, not just by code review.

---

## Phase 4 — Employee, Department, Branch Management

**Goal:** Org Admin can build out their organization's structure.

- `Department`, `Branch`, `Shift`, `ManagerAssignment`, `Employee` models.
- Employee CRUD with temp-password issuance on create (integrates with
  Phase 2's `must_change_password`); soft-delete (`employment_status`)
  instead of hard delete.
- Department/Branch/Shift CRUD, Org Admin only.
- "Capture Current Location" flow: browser Geolocation API →
  `POST /branches` / `capture-location` — no manual lat/lng input field
  exists in the UI at all (enforces the brief's requirement at the UX
  layer, backed by the API-layer requirement from Architecture §6.4).
- `AttendanceRule` model + settings UI (working days, start/end time,
  late threshold) — configured now so Phase 5 has something to read.
- Manager scoping: Manager role can list only their assigned
  department(s)/employees.
- Org Admin Web: Employees, Departments, Branches, Shifts, Settings pages
  with full CRUD, search, pagination.
- Profile picture upload flow (signed Supabase Storage URL, MIME/size
  validation, EXIF stripping) — used by both employee self-service
  (Phase 5 mobile) and admin-set pictures.
- Tests: temp-password + forced change round-trip; Manager cannot see
  employees outside their assignment; branch location capture rejects
  payloads missing `gps_accuracy`.

**Acceptance:** an Org Admin can fully staff their organization (branches,
departments, shifts, employees, manager assignments) and configure
attendance rules, entirely through the UI, with data fully isolated per
org.

---

## Phase 5 — Attendance: GPS, Geofencing, Check-in/Check-out

**Goal:** the core product feature works correctly and is hard to spoof.

- `Attendance` model; `domain/geofence.py` (Haversine, pure function,
  100% unit-tested with known coordinate pairs); `domain/rules.py`
  (status calculation: present/late/early-departure/absent/overtime
  against `AttendanceRule` + assigned `Shift`).
- `CheckInService` / `CheckOutService` (application layer) orchestrating:
  auth → org → branch → distance → accuracy → mock-location →
  schedule → persist, each step raising a specific domain exception
  mapped to the API error codes in the API spec.
- `SecurityEvent` logging for mock-location detections and implausible-
  travel-speed detections.
- Mobile: location permission flow, `CheckInScreen` (distance/accuracy
  shown to the user before submit where feasible), dashboard "today's
  status" card, attendance history list.
- Org Admin Web: live attendance list/filter by branch/department/date/
  status; dashboard cards (present/absent/late/on-leave) wired to real
  data.
- Notifications: check-in/check-out success notifications (in-app +
  push) via the `NotificationDispatcher` stub (full multi-channel wiring
  in Phase 7 — v1 here can be in-app + push only).
- Tests (this is the highest-risk phase — test depth matters more here
  than anywhere else): geofence boundary cases (exactly at radius,
  1m inside/outside), accuracy boundary cases, duplicate check-in
  rejection, check-out-without-check-in rejection, status calculation
  against every threshold example in the brief (§13's 08:10 vs 08:00 →
  Late by 10 example is a literal test case), mock-location denial.

**Acceptance:** an employee physically at a configured branch can check
in/out and see correct status; the same request replayed from a spoofed
location a mocked-GPS app reports is denied and logged; late-arrival
minutes match the brief's worked example exactly.

---

## Phase 6 — Reporting & Dashboards

**Goal:** the data collected in Phase 5 is visible, exportable, and fast.

- Report aggregation services (daily/weekly/monthly/employee/department/
  late/overtime) — read-optimized queries against the indexes from ERD
  §4, cached where the brief's "thousands of orgs / millions of records"
  scale requires it.
- Celery async export pipeline: PDF (e.g. WeasyPrint/ReportLab) and Excel
  (openpyxl) generation, job-status polling endpoint, signed download URL
  from Supabase Storage.
- Org Admin Web: Reports page with filters, charts (attendance trends,
  department attendance, monthly view), export buttons.
- Super Admin Web: platform dashboard charts (org growth, active vs
  expired subscriptions, system activity) using the same charting
  approach for consistency.
- Tests: report totals reconciled against raw `Attendance` rows for a
  seeded dataset (no silent aggregation bugs); export job completes and
  produces a valid file.

**Acceptance:** every report listed in brief §20 is viewable and
exportable in both formats; dashboards load within an acceptable budget
against a seeded dataset of realistic size (tens of thousands of
attendance rows).

---

## Phase 7 — Notifications (Full) & Leave Management

**Goal:** the two remaining brief features (leave workflow, full
notification fan-out) are complete.

- `LeaveType`, `LeaveRequest`, `LeaveBalance` models; submit → approve/
  reject workflow (Manager/Org Admin); balance decremented on approval,
  restored on later cancellation if applicable.
- Mobile: Leave request screen, leave history.
- Org Admin Web: Leave list, approve/reject UI, balance view.
- `NotificationDispatcher` fully wired: in-app (all events from brief
  §21), email (password changes, leave decisions, security alerts),
  push (attendance + leave), SMS-ready interface with a documented no-op
  implementation.
- New-device-login detection wired to `Device`/`LoginHistory` →
  notification to employee and Org Admin per brief §21.
- Tests: leave balance arithmetic across multiple requests/years; approval
  permission boundaries (Manager can only approve within their scope);
  notification fan-out reaches the right audience for each event type.

**Acceptance:** full leave lifecycle works with correct balance tracking;
every notification event listed in brief §21 fires to the correct
audience through at least in-app + one other channel.

---

## Phase 8 — Subscription System

**Goal:** the SaaS commercial layer is real, not just a status flag.

- Subscription plan management (already scaffolded in Phase 3) extended
  with expiry automation: Celery Beat daily job flips `Subscription.status`
  on expiry, notifies Org Admin ahead of expiry (7/3/1-day warnings) and
  on lapse, and blocks non-Super-Admin login once fully expired (grace
  period configurable per plan).
- Billing/payment integration: **flagged as an open decision in
  Architecture §12** — if in scope, integrate a payment provider here
  (Stripe and/or a Tanzanian mobile-money gateway); if out of scope for
  v1, this phase ships admin-managed subscription status only, with the
  data model already shaped to add billing later without migration.
- Super Admin Web: subscription management UI, expiry monitoring view.

**Acceptance:** subscription expiry is enforced automatically without
manual Super Admin intervention; warnings are sent on schedule.

---

## Phase 9 — Testing, Hardening & Deployment

**Goal:** production-ready.

- Backend: fill remaining unit/integration/permission/API test gaps
  toward meaningful coverage of every module in brief §32; load-test the
  check-in endpoint specifically (it is the highest-traffic, most
  latency-sensitive path — twice daily per employee, clustered at shift
  start/end).
- Frontend: component tests (React Testing Library) for forms
  (validation) and key pages; mobile authentication + location-permission
  flow tests.
- Security pass: run through Architecture §6 checklist end-to-end
  (headers, CORS, rate limits, RLS policies active in staging, dependency
  vulnerability scan); confirm no secret is hardcoded anywhere (`git
  grep` for likely leaked keys as a final gate).
- i18n pass: confirm English/Kiswahili coverage of all user-facing
  strings, not just happy-path screens.
- Accessibility pass: keyboard navigation, color contrast, form error
  messaging on both web apps.
- Render production environment stood up: production Supabase project,
  production env vars set (never copied from staging), migrations run as
  a release step, Celery worker + beat services running, static sites
  built with production `VITE_API_BASE_URL`.
- Runbook/README: how to deploy, how to roll back, how to rotate secrets,
  how to onboard a new organization (Super Admin walkthrough).

**Acceptance:** the system in Architecture §9's deployment diagram is
live on Render + Supabase, passes the security checklist, and a fresh
organization can be onboarded and used end-to-end (create org → create
admin → admin creates branch + employees → employee checks in from a real
phone at the branch location → admin sees it on the dashboard → report
exports correctly) without manual DB intervention.

---

## Sequencing Notes

- Phases 2 and 3 are tightly coupled (auth needs `Organization` to exist
  for the login triple; tenancy needs `UserAccount` to carry the claim) —
  they are listed separately because the brief does, but in practice the
  `Organization` model's minimal shape ships at the start of Phase 2, and
  full org-management CRUD lands in Phase 3.
- Phase 5 (attendance) is the critical path and the highest-risk phase —
  do not compress its test-writing to "make room" for later phases;
  everything downstream (reports, dashboards, notifications) is a
  consumer of `Attendance` data and inherits any correctness bug in it
  silently.
- Phases 6–8 can partially overlap once Phase 5 is stable (e.g., reporting
  and leave management touch mostly disjoint code) if there is more than
  one engineer — called out here so the roadmap doesn't imply strict
  single-threaded sequencing is mandatory, only that dependencies must be
  respected.

---

## Next Step

Awaiting your review/approval of this document, the ERD (`02-DATABASE-ERD.md`),
the API spec (`03-API-SPECIFICATION.md`), and the folder structure
(`04-PROJECT-STRUCTURE.md`), plus a decision on the four open items in
`01-SYSTEM-ARCHITECTURE.md` §12, before Phase 1 implementation begins.
