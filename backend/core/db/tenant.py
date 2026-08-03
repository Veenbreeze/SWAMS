"""Tenant-scoped model base — see docs/01-SYSTEM-ARCHITECTURE.md §4.1.

`TenantManager.get_queryset()` filters by the request-scoped
`current_organization_id` contextvar (bound by
`core.middleware.tenant_middleware.TenantAwareJWTAuthentication`).

Crucially, when no organization is bound — a Super Admin request
(platform-wide, `organization_id IS NULL`), a Celery task, a management
command, or simply a bug where the context was never set — the default
manager returns an **empty** queryset, not every row. A forgotten filter
must fail closed, not open. Code that legitimately needs cross-tenant
access (Super Admin platform endpoints, background jobs operating on all
organizations) must say so explicitly via `.all_tenants()`.

Do not retrofit `UserAccount` onto this base: login resolves *which* user
is signing in before any JWT — and therefore any tenant context — exists,
so its lookups are necessarily done via explicit `organization=` filters
against the plain manager (see apps/authentication/services.py). Every
tenant-scoped model created from Phase 3 onward should use this base.
"""

from django.db import models

from core.middleware.tenant_context import current_organization_id


class TenantManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        org_id = current_organization_id.get()
        if org_id is None:
            return qs.none()
        return qs.filter(organization_id=org_id)

    def all_tenants(self):
        """Explicit, deliberate opt-out of tenant filtering.

        Caution: on a *reverse related manager* (e.g. `organization.things`
        for a `things = ForeignKey(Organization, related_name="things")`),
        this returns every row for every organization, not just the
        parent's — Django generates the related manager as a runtime
        subclass of TenantManager, and this method's `super().get_queryset()`
        walks the MRO from TenantManager upward, past the related
        manager's own `.filter(fk=parent)` override, never back down to
        it. To get "all of THIS organization's rows regardless of the
        ambient tenant context", call `Model.objects.all_tenants().filter(
        organization=instance)` on the base manager instead of
        `instance.related_name.all_tenants()`.
        """
        return super().get_queryset()


class TenantModel(models.Model):
    objects = TenantManager()

    class Meta:
        abstract = True
