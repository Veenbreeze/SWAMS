# SWAMS — Repository & Folder Structure

Monorepo layout at `C:\Users\mpamb\Desktop\AMS` (three deployable projects,
one repo, shared docs):

```
AMS/
  docs/                          # this documentation set
  backend/                       # Django + DRF
  frontend-org-admin/            # React (Vite) — Organization Admin Web
  frontend-super-admin/          # React (Vite) — Super Admin Web
  mobile/                        # Expo React Native — Employee app
  README.md
```

Two separate Vite apps (not one app with role-based routing) because the
brief treats them as genuinely separate applications with different deploy
targets, different audiences, and mostly non-overlapping features — a
shared `packages/ui` could be introduced later if duplication becomes
painful, but is not justified for two apps yet.

---

## 1. Backend — `backend/`

```
backend/
  manage.py
  requirements/
    base.txt
    local.txt
    production.txt
  core/
    settings/
      base.py
      local.py
      staging.py
      production.py
    middleware/
      tenant_middleware.py
      security_headers.py
    permissions/
      roles.py              # IsSuperAdmin, IsOrgAdmin, IsManagerOrAbove, IsSelf
      object_level.py        # SameOrganization, ManagerScope
    exceptions.py            # DRF custom exception handler -> uniform error envelope
    pagination.py
    celery.py
    urls.py
    wsgi.py / asgi.py
  apps/
    authentication/
      domain/
      application/
      infrastructure/
        models.py            # UserAccount, RefreshToken, LoginHistory, Device
      interfaces/
        serializers.py
        views.py
        urls.py
      tests/
    organizations/
      infrastructure/models.py   # Organization
      ...
    subscriptions/
      infrastructure/models.py   # SubscriptionPlan, Subscription
      tasks.py                    # Celery: expiry checks, renewal reminders
      ...
    employees/
      infrastructure/models.py   # Employee, Department, ManagerAssignment
      ...
    locations/
      infrastructure/models.py   # Branch
      domain/geofence.py          # Haversine distance, pure function
      ...
    attendance/
      domain/
        entities.py                # AttendanceRecord, GeofenceCheck
        rules.py                   # status calculation (present/late/absent/overtime)
        exceptions.py
      application/
        services.py                # CheckInService, CheckOutService
        interfaces.py               # AttendanceRepository (port)
      infrastructure/
        models.py                  # Attendance, Shift, AttendanceRule
        repositories.py            # ORM implementation of the port
      interfaces/
        serializers.py
        views.py
        urls.py
      tests/
        test_geofence.py
        test_status_calculation.py
        test_check_in_api.py
    leave/
      infrastructure/models.py    # LeaveType, LeaveRequest, LeaveBalance
      ...
    notifications/
      infrastructure/models.py    # Notification
      services/
        dispatcher.py              # NotificationDispatcher (in-app/email/push/sms)
        push.py                    # Expo push
        email.py
        sms.py                     # no-op provider + interface, SMS-ready
      tasks.py
      ...
    reports/
      services/
        aggregations.py
        exporters/
          pdf.py
          excel.py
      tasks.py                     # async report generation
      ...
    audit_logs/
      infrastructure/models.py    # AuditLog
      services.py                  # AuditLogger.record(...)
      ...
    security/
      infrastructure/models.py    # SecurityEvent
      services.py                  # mock-location detection, lockout logic
      ...
  storage/
    supabase_client.py            # signed URL issuance for uploads
  tests/
    factories.py                  # factory_boy factories (Organization, Employee, ...)
    conftest.py
  Dockerfile                       # optional, Render can also build natively
  render.yaml                      # Render Blueprint (web, worker, beat, redis)
  .env.example
```

Why `domain/application/infrastructure/interfaces` only on the apps where
it earns its keep (`attendance`, `locations`) and a flatter structure
elsewhere (`organizations`, `departments`): the geofence/status-calculation
logic is the one piece of real, test-worthy business logic; CRUD-shaped
apps (departments, branches metadata) don't benefit from the extra layering
and it would just be ceremony. This is a deliberate, documented exception
to "layer everything the same way" — consistency is not free, and forcing
four folders onto a five-field CRUD app would cost more in navigation
friction than it returns in testability.

---

## 2. Organization Admin Web — `frontend-org-admin/`

```
frontend-org-admin/
  index.html
  vite.config.js
  tailwind.config.js
  .env.example
  src/
    main.jsx
    App.jsx
    routes/
      index.jsx                 # React Router route tree
      ProtectedRoute.jsx         # role guard (UX only — see Security Architecture)
    layouts/
      DashboardLayout.jsx
      AuthLayout.jsx
    pages/
      auth/Login.jsx
      dashboard/Dashboard.jsx
      employees/EmployeeList.jsx
      employees/EmployeeDetail.jsx
      departments/DepartmentList.jsx
      branches/BranchList.jsx
      branches/CaptureLocation.jsx   # browser Geolocation capture UI
      attendance/AttendanceList.jsx
      reports/Reports.jsx
      leaves/LeaveList.jsx
      notifications/Notifications.jsx
      settings/Settings.jsx
    components/
      ui/                        # shadcn/ui primitives
      charts/
      tables/
      forms/
    hooks/
      useAuth.js
      usePermissions.js
    context/
      AuthContext.jsx
      TenantContext.jsx
    api/
      client.js                  # Axios instance, interceptors (refresh, error envelope)
      endpoints/
        auth.js
        employees.js
        attendance.js
        ...
    services/
      queryKeys.js                # React Query key factory
    i18n/
      en.json
      sw.json
    utils/
    assets/
```

## 3. Super Admin Web — `frontend-super-admin/`

Same skeleton as above, smaller surface:

```
frontend-super-admin/
  src/
    pages/
      organizations/OrganizationList.jsx
      organizations/OrganizationDetail.jsx
      subscriptions/PlanList.jsx
      dashboard/Dashboard.jsx
      audit-logs/AuditLogViewer.jsx
      security/SecurityEvents.jsx
      settings/PlatformSettings.jsx
    ... (components/hooks/context/api/i18n/utils/assets mirrors org-admin)
```

## 4. Mobile — `mobile/`

```
mobile/
  app.json                        # Expo config (permissions: location, camera, notifications)
  eas.json
  babel.config.js
  .env.example
  src/
    navigation/
      RootNavigator.js
      AuthNavigator.js
      AppTabNavigator.js
    screens/
      SplashScreen.js
      auth/LoginScreen.js
      auth/ForceChangePasswordScreen.js
      dashboard/DashboardScreen.js
      attendance/CheckInScreen.js
      attendance/HistoryScreen.js
      leave/LeaveRequestScreen.js
      leave/LeaveHistoryScreen.js
      profile/ProfileScreen.js
      settings/SettingsScreen.js
    components/
    services/
      api/
        client.js                 # Axios + interceptors
        endpoints/
      location/
        geolocation.js             # expo-location wrapper, accuracy request, mock-location flag (Android)
      notifications/
        push.js                    # expo-notifications registration
      camera/
        profilePicture.js
    storage/
      secureStore.js               # expo-secure-store wrapper for tokens
    hooks/
      useAuth.js
      useLocation.js
    context/
      AuthContext.js
    i18n/
    utils/
```

---

## 5. Shared Conventions

- Every frontend/mobile API call goes through one Axios instance per app
  with a response interceptor that (a) unwraps the uniform error envelope,
  (b) on `401 TOKEN_EXPIRED` attempts one silent refresh + retry, (c) on
  refresh failure forces logout.
- No app ever constructs a "can I see this" decision from local
  state alone for anything destructive — buttons may be hidden for UX, but
  the underlying API call is what's actually gated (server already
  enforces it either way).
- Environment variables (all apps): `.env.example` checked in,
  `.env` gitignored; Render env vars set per-service in the dashboard,
  never committed.
