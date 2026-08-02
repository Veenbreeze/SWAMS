# SWAMS — Smart Workforce Attendance Management System

A multi-tenant SaaS platform for GPS/geofence-based employee attendance,
built for organizations in Tanzania and beyond.

**Status:** Architecture & design phase — no application code yet, per the
project's phased development process (see roadmap).

## Design Documents

Read in this order before any implementation work begins:

1. [`docs/01-SYSTEM-ARCHITECTURE.md`](docs/01-SYSTEM-ARCHITECTURE.md) —
   architecture, multi-tenancy model, RBAC, security design, deployment
   topology, open decisions requiring sign-off.
2. [`docs/02-DATABASE-ERD.md`](docs/02-DATABASE-ERD.md) — full entity
   relationship diagram, table rationale, indexing, RLS, backup strategy.
3. [`docs/03-API-SPECIFICATION.md`](docs/03-API-SPECIFICATION.md) — REST
   API contract for all three client apps.
4. [`docs/04-PROJECT-STRUCTURE.md`](docs/04-PROJECT-STRUCTURE.md) —
   repository/folder layout for backend, both web apps, and mobile.
5. [`docs/05-DEVELOPMENT-ROADMAP.md`](docs/05-DEVELOPMENT-ROADMAP.md) —
   phased implementation plan with acceptance criteria per phase.

## Stack

- Backend: Python, Django, Django REST Framework, PostgreSQL (Supabase),
  Celery + Redis
- Web (Super Admin & Organization Admin): React.js (JavaScript, no
  TypeScript), Vite, Tailwind CSS, shadcn/ui, React Router, React Query
- Mobile (Employee app): React Native, Expo
- File storage: Supabase Storage
- Deployment: Render (backend + both web apps), Supabase (DB + storage)

## Applications

- `frontend-super-admin/` — platform owner control plane
- `frontend-org-admin/` — per-organization HR/admin back office
- `mobile/` — employee check-in/check-out app
- `backend/` — shared Django REST API serving all three
