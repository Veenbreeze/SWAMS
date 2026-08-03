import uuid

from django.db import models

from core.db.tenant import TenantModel


class ExportFormat(models.TextChoices):
    PDF = "pdf", "PDF"
    XLSX = "xlsx", "Excel"


class ExportStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"


class ReportExportJob(TenantModel):
    """Tracks one async PDF/Excel export — see
    docs/03-API-SPECIFICATION.md §11 (`POST /reports/{report}/export` ->
    `{job_id}`, poll `GET /reports/jobs/{job_id}`) and
    docs/05-DEVELOPMENT-ROADMAP.md Phase 6.

    `params` freezes everything the Celery task (`apps/reports/tasks.py`)
    needs to reproduce the exact same report a synchronous
    `GET /reports/...` call would have returned — including
    `employee_ids`, the caller's resolved Manager-scope at request time,
    captured now rather than re-derived inside the task (the task has no
    `request.user` to re-derive it from).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="report_export_jobs"
    )
    requested_by = models.ForeignKey(
        "authentication.UserAccount", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    report_type = models.CharField(max_length=20)
    params = models.JSONField(default=dict, blank=True)
    format = models.CharField(max_length=10, choices=ExportFormat.choices)
    status = models.CharField(
        max_length=20, choices=ExportStatus.choices, default=ExportStatus.PENDING
    )
    file_path = models.CharField(max_length=500, blank=True)
    download_url = models.URLField(blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "requested_by", "-created_at"])]

    def __str__(self):
        return f"{self.report_type} export ({self.format}) — {self.status}"
