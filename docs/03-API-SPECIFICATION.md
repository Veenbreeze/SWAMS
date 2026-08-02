# SWAMS — API Specification (v1)

Base URL: `https://api.swams.app/api/v1/` (per-environment host via env var)

All endpoints (except `/auth/login`, `/auth/refresh`, `/auth/password-reset*`,
`/health`) require `Authorization: Bearer <access_token>`.

## Conventions

- Content type: `application/json` for all requests/responses; file uploads
  use presigned Supabase Storage URLs (see §7), not multipart-to-Django.
- Pagination: list endpoints return
  `{ "count": n, "next": url|null, "previous": url|null, "results": [...] }`.
  `Attendance` history uses cursor pagination (`?cursor=...`); everything
  else uses page-number (`?page=`, `?page_size=`).
- Errors: uniform envelope —
  ```json
  {
    "error": {
      "code": "OUTSIDE_GEOFENCE",
      "message": "You are outside the authorized workplace location.",
      "details": {}
    }
  }
  ```
  `code` is a stable machine-readable string the mobile/web apps can switch
  on for localization; `message` is a fallback/default-locale string —
  clients should localize by `code`, not by string-matching `message`.
- Versioning: URL-prefixed (`/api/v1/`); breaking changes ship as `/api/v2/`
  behind a deprecation window, never as a silent behavior change on v1.
- Idempotency: `check-in`/`check-out` are naturally idempotent per
  `(employee_id, attendance_date)` — a repeat check-in call returns the
  existing record with `409 Conflict` rather than creating a duplicate.

---

## 1. Authentication — `/api/v1/auth/`

### `POST /auth/login`
```json
// Request (Org Admin / Manager / Employee)
{ "organization_code": "ABC001", "identifier": "john@example.com", "password": "..." }

// Request (Super Admin — no organization_code; resolves against
// platform-wide accounts where organization_id IS NULL)
{ "identifier": "owner@swams.app", "password": "..." }

// Response 200
{
  "access_token": "...",
  "refresh_token": "...",
  "must_change_password": false,
  "user": { "id": "...", "role": "EMPLOYEE", "organization_id": "...", "employee": { ... } }
}
```
`organization_code` is optional: omitted, the login resolves only against
platform-wide (`organization_id IS NULL`) accounts — i.e. Super Admin only.
Provided, it resolves a tenant-scoped account within that organization.
A request cannot match both a platform account and a tenant account, so
this is unambiguous.
Errors: `401 INVALID_CREDENTIALS`, `403 ACCOUNT_LOCKED`, `403
ORGANIZATION_SUSPENDED`, `404 ORGANIZATION_NOT_FOUND`. Rate-limited
per `(organization_code, identifier)` and per-IP.

### `POST /auth/refresh`
`{ "refresh_token": "..." }` → new `access_token` + rotated `refresh_token`.
Reused/blacklisted token → `401 TOKEN_REUSE_DETECTED` and all sessions for
that user are revoked server-side.

### `POST /auth/logout`
Revokes the presented refresh token.

### `POST /auth/logout-all`
Revokes all refresh tokens for the authenticated user (§22 "Logout from all
devices").

### `POST /auth/change-password`
`{ "current_password": "...", "new_password": "..." }` — also clears
`must_change_password`. Enforced complexity rules (min length, mixed
character classes) validated server-side.

### `POST /auth/password-reset/request`
`{ "organization_code": "...", "identifier": "..." }` — always returns
`200` regardless of whether the account exists (prevents account
enumeration); sends email with time-limited reset token if it does.

### `POST /auth/password-reset/confirm`
`{ "token": "...", "new_password": "..." }`

---

## 2. Platform (Super Admin) — `/api/v1/platform/`

All require `role=SUPER_ADMIN`.

| Method | Path | Description |
|---|---|---|
| GET | `/platform/organizations` | List organizations, filter by status/plan |
| POST | `/platform/organizations` | Create organization + its first Org Admin |
| GET | `/platform/organizations/{id}` | Organization detail |
| PATCH | `/platform/organizations/{id}` | Edit organization |
| POST | `/platform/organizations/{id}/suspend` | Suspend |
| POST | `/platform/organizations/{id}/activate` | Activate |
| GET | `/platform/subscription-plans` | List plans |
| POST | `/platform/subscription-plans` | Create plan |
| PATCH | `/platform/subscription-plans/{id}` | Edit plan |
| GET | `/platform/organizations/{id}/subscriptions` | Subscription history |
| POST | `/platform/organizations/{id}/subscriptions` | Assign/renew subscription |
| GET | `/platform/stats` | Platform-wide dashboard numbers |
| GET | `/platform/audit-logs` | System-wide audit log (read-only, filterable) |
| GET | `/platform/security-events` | Security events across all orgs |

---

## 3. Organizations (self) — `/api/v1/organizations/`

| Method | Path | Description | Roles |
|---|---|---|---|
| GET | `/organizations/me` | Current org profile | Org Admin, Manager, Employee (limited fields) |
| PATCH | `/organizations/me` | Edit own org profile (name, logo, contact) | Org Admin |

---

## 4. Departments — `/api/v1/departments/`

| Method | Path | Roles |
|---|---|---|
| GET | `/departments` | Org Admin, Manager |
| POST | `/departments` | Org Admin |
| GET | `/departments/{id}` | Org Admin, Manager |
| PATCH | `/departments/{id}` | Org Admin |
| DELETE | `/departments/{id}` | Org Admin (blocked if employees assigned) |

## 5. Branches — `/api/v1/branches/`

| Method | Path | Roles |
|---|---|---|
| GET | `/branches` | Org Admin, Manager |
| POST | `/branches` | Org Admin |
| PATCH | `/branches/{id}` | Org Admin |
| DELETE | `/branches/{id}` | Org Admin |
| POST | `/branches/{id}/capture-location` | Org Admin |

`POST /branches` and `capture-location` accept
`{ "latitude": ..., "longitude": ..., "gps_accuracy": ... }` captured by the
admin's own browser/device Geolocation API at the moment of the call — the
API rejects payloads without an accompanying `gps_accuracy` (no manual
lat/lng-only entry path exists, per the brief's explicit requirement).

## 6. Shifts — `/api/v1/shifts/`

Standard CRUD, Org Admin only for write, Manager/Employee read own.

## 7. Employees — `/api/v1/employees/`

| Method | Path | Roles |
|---|---|---|
| GET | `/employees` | Org Admin, Manager (scoped) |
| POST | `/employees` | Org Admin — creates `UserAccount` + `Employee`, temp password, `must_change_password=true` |
| GET | `/employees/{id}` | Org Admin, Manager (scoped), self |
| PATCH | `/employees/{id}` | Org Admin (full), self (limited: phone, profile picture — enforced by a distinct serializer, see Architecture §5) |
| DELETE | `/employees/{id}` | Org Admin (soft delete — `employment_status=TERMINATED`, retains attendance history) |
| POST | `/employees/{id}/reset-password` | Org Admin — issues new temp password, sets `must_change_password=true` |
| POST | `/employees/{id}/profile-picture` | self, Org Admin — returns a signed Supabase Storage upload URL |

## 8. Attendance — `/api/v1/attendance/`

| Method | Path | Roles |
|---|---|---|
| POST | `/attendance/check-in` | Employee |
| POST | `/attendance/check-out` | Employee |
| GET | `/attendance/history` | Employee (self), Org Admin/Manager (any within scope, via `?employee_id=`) |
| GET | `/attendance/today` | Employee — today's status for dashboard |
| GET | `/attendance` | Org Admin, Manager — list/filter by branch/department/date/status |
| GET | `/attendance/{id}` | Org Admin, Manager, self |

### `POST /attendance/check-in`
```json
{
  "latitude": -6.792354,
  "longitude": 39.208328,
  "accuracy": 8.5,
  "device_id": "expo-installation-id",
  "is_mock_location": false,
  "client_timestamp": "2026-08-02T08:10:00+03:00"
}
```
Response `201`:
```json
{
  "id": "...", "status": "LATE", "late_minutes": 10,
  "check_in_time": "2026-08-02T08:10:03Z", "branch": { "name": "Head Office" }
}
```
Denial responses (`422`):
- `OUTSIDE_GEOFENCE` — "You are outside the authorized workplace location."
- `POOR_GPS_ACCURACY` — "Unable to verify your location. Please move to an
  open area and try again."
- `MOCK_LOCATION_DETECTED` — logged as `SecurityEvent`, generic denial
  message shown to user (does not reveal detection to a would-be spoofer).
- `ALREADY_CHECKED_IN` (`409`)
- `NOT_A_WORKING_DAY` / `OUTSIDE_SHIFT_WINDOW` (soft warnings — configurable
  whether these block or just annotate the record, per org's
  `AttendanceRule`).

### `POST /attendance/check-out`
Same payload shape and same validation pipeline; `400
NOT_CHECKED_IN_YET` if there's no open check-in for today.

## 9. Leave — `/api/v1/leave/`

| Method | Path | Roles |
|---|---|---|
| GET | `/leave/types` | all |
| GET | `/leave/requests` | self (own), Manager/Org Admin (scoped) |
| POST | `/leave/requests` | Employee |
| PATCH | `/leave/requests/{id}` | Employee (own, only while `PENDING` — can edit/withdraw) |
| POST | `/leave/requests/{id}/approve` | Manager, Org Admin |
| POST | `/leave/requests/{id}/reject` | Manager, Org Admin (requires `reason`) |
| GET | `/leave/balance` | self, Manager/Org Admin (scoped) |

## 10. Notifications — `/api/v1/notifications/`

| Method | Path |
|---|---|
| GET | `/notifications` |
| POST | `/notifications/{id}/read` |
| POST | `/notifications/read-all` |
| POST | `/notifications/register-device` — `{ device_id, push_token, platform }` |

## 11. Reports — `/api/v1/reports/`

| Method | Path | Description |
|---|---|---|
| GET | `/reports/daily?date=` | Daily attendance summary |
| GET | `/reports/weekly?start=` | Weekly report |
| GET | `/reports/monthly?month=` | Monthly report |
| GET | `/reports/employee/{id}` | Per-employee report |
| GET | `/reports/department/{id}` | Per-department report |
| GET | `/reports/late` | Late-attendance report |
| GET | `/reports/overtime` | Overtime report |
| GET | `/reports/{report}/export?format=pdf|xlsx` | Async job → returns `{ job_id }`; poll `/reports/jobs/{job_id}` for a signed download URL once Celery finishes |

## 12. Audit & Security (org-scoped) — `/api/v1/audit-logs/`

| Method | Path | Roles |
|---|---|---|
| GET | `/audit-logs` | Org Admin (own org only) |

Org Admins see only their own organization's audit trail; platform-wide
audit/security views are Super-Admin-only (§2).

## 13. Dashboard — `/api/v1/dashboard/`

| Method | Path | Description |
|---|---|---|
| GET | `/dashboard/org-admin` | Total/present/absent/late/on-leave cards + trend series |
| GET | `/dashboard/employee` | Today's status, this month's summary, unread notification count |
| GET | `/dashboard/super-admin` | Total/active orgs, expired subs, total users, system activity |

## 14. Health

`GET /health` — unauthenticated, used by Render health checks; returns DB
connectivity status.

---

## Error Code Reference (partial, extended as built)

| Code | HTTP | Meaning |
|---|---|---|
| `INVALID_CREDENTIALS` | 401 | Bad org code / identifier / password |
| `ACCOUNT_LOCKED` | 403 | Too many failed attempts |
| `ORGANIZATION_SUSPENDED` | 403 | Org subscription/status blocks login |
| `MUST_CHANGE_PASSWORD` | 403 | Blocks all endpoints except change-password |
| `TOKEN_EXPIRED` / `TOKEN_INVALID` | 401 | JWT problems |
| `TOKEN_REUSE_DETECTED` | 401 | Refresh-token replay — all sessions revoked |
| `PERMISSION_DENIED` | 403 | Role/object-level authorization failure |
| `CROSS_TENANT_ACCESS` | 403 | Attempt to reach another org's resource (also logged as SecurityEvent) |
| `OUTSIDE_GEOFENCE` | 422 | Distance > branch radius |
| `POOR_GPS_ACCURACY` | 422 | Accuracy > branch limit |
| `MOCK_LOCATION_DETECTED` | 422 | Spoofing indicator present |
| `ALREADY_CHECKED_IN` / `NOT_CHECKED_IN_YET` | 409/400 | Attendance state conflict |
| `VALIDATION_ERROR` | 400 | Generic field validation failure, `details` has per-field errors |
| `RATE_LIMITED` | 429 | Throttle exceeded |
