from rest_framework import serializers

from apps.reports.models import ReportExportJob


class DailySummarySerializer(serializers.Serializer):
    date = serializers.DateField()
    is_working_day = serializers.BooleanField()
    total_employees = serializers.IntegerField()
    present = serializers.IntegerField()
    late = serializers.IntegerField()
    early_departure = serializers.IntegerField()
    overtime = serializers.IntegerField()
    absent = serializers.IntegerField(allow_null=True)


class RangeTotalsSerializer(serializers.Serializer):
    present = serializers.IntegerField()
    late = serializers.IntegerField()
    early_departure = serializers.IntegerField()
    overtime = serializers.IntegerField()
    absent = serializers.IntegerField()


class RangeSummarySerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    days = DailySummarySerializer(many=True)
    totals = RangeTotalsSerializer()


class DepartmentReportSerializer(RangeSummarySerializer):
    department_id = serializers.UUIDField()
    department_name = serializers.CharField()


class EmployeeReportTotalsSerializer(serializers.Serializer):
    days_present = serializers.IntegerField()
    days_late = serializers.IntegerField()
    total_late_minutes = serializers.IntegerField()
    total_early_departure_minutes = serializers.IntegerField()
    total_overtime_minutes = serializers.IntegerField()
    total_working_minutes = serializers.IntegerField()


class ReportExportJobSerializer(serializers.ModelSerializer):
    job_id = serializers.UUIDField(source="id", read_only=True)

    class Meta:
        model = ReportExportJob
        fields = [
            "job_id",
            "report_type",
            "format",
            "status",
            "download_url",
            "error_message",
            "created_at",
            "completed_at",
        ]
        read_only_fields = fields
