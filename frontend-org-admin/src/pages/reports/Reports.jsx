import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { getExportJob, getMonthlyReport, requestReportExport } from "@/api/endpoints/reports";
import { AttendanceTrendChart } from "@/components/charts/AttendanceTrendChart";
import { Button } from "@/components/ui/button";

function currentMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

const POLL_INTERVAL_MS = 1500;

export default function Reports() {
  const { t } = useTranslation();
  const [month, setMonth] = useState(currentMonth());
  const [exportJobs, setExportJobs] = useState({});
  const pollHandles = useRef({});

  const { data, isLoading, isError } = useQuery({
    queryKey: ["reports", "monthly", month],
    queryFn: () => getMonthlyReport({ month }),
  });

  useEffect(() => {
    const handles = pollHandles.current;
    return () => {
      Object.values(handles).forEach(clearInterval);
    };
  }, []);

  const pollJob = useCallback((format, jobId) => {
    pollHandles.current[format] = setInterval(async () => {
      try {
        const job = await getExportJob(jobId);
        setExportJobs((prev) => ({ ...prev, [format]: job }));
        if (job.status === "COMPLETED" || job.status === "FAILED") {
          clearInterval(pollHandles.current[format]);
        }
      } catch {
        clearInterval(pollHandles.current[format]);
        setExportJobs((prev) => ({ ...prev, [format]: { status: "FAILED" } }));
      }
    }, POLL_INTERVAL_MS);
  }, []);

  async function handleExport(format) {
    setExportJobs((prev) => ({ ...prev, [format]: { status: "PENDING" } }));
    try {
      const { job_id: jobId } = await requestReportExport("monthly", { month, format });
      pollJob(format, jobId);
    } catch {
      setExportJobs((prev) => ({ ...prev, [format]: { status: "FAILED" } }));
    }
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="font-heading text-2xl font-semibold">{t("reports.title")}</h1>
        <input
          type="month"
          value={month}
          onChange={(event) => setMonth(event.target.value)}
          className="h-8 rounded-lg border border-border bg-background px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
        />
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">{t("reports.loading")}</p>}
      {isError && (
        <p role="alert" className="text-sm text-destructive">
          {t("reports.error")}
        </p>
      )}

      {data && (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <SummaryStat label={t("reports.present")} value={data.totals.present} />
            <SummaryStat label={t("reports.late")} value={data.totals.late} />
            <SummaryStat label={t("reports.earlyDeparture")} value={data.totals.early_departure} />
            <SummaryStat label={t("reports.overtime")} value={data.totals.overtime} />
          </div>

          <div className="rounded-xl border bg-card p-4">
            <h2 className="mb-4 font-heading text-base font-medium">{t("reports.dailyAttendance")}</h2>
            <AttendanceTrendChart data={data.days} />
          </div>

          <div className="flex items-center gap-4">
            <ExportButton
              label={t("reports.exportPdf")}
              job={exportJobs.pdf}
              onClick={() => handleExport("pdf")}
            />
            <ExportButton
              label={t("reports.exportXlsx")}
              job={exportJobs.xlsx}
              onClick={() => handleExport("xlsx")}
            />
          </div>
        </>
      )}
    </div>
  );
}

function SummaryStat({ label, value }) {
  return (
    <div className="rounded-xl border bg-card p-4">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="text-2xl font-semibold tabular-nums">{value}</p>
    </div>
  );
}

function ExportButton({ label, job, onClick }) {
  const { t } = useTranslation();
  const isBusy = job?.status === "PENDING" || job?.status === "PROCESSING";

  return (
    <div className="flex items-center gap-2">
      <Button variant="outline" disabled={isBusy} onClick={onClick}>
        {isBusy ? t("reports.preparing") : label}
      </Button>
      {job?.status === "COMPLETED" && (
        <a
          href={job.download_url}
          target="_blank"
          rel="noreferrer"
          className="text-sm text-primary underline-offset-4 hover:underline"
        >
          {t("reports.download")}
        </a>
      )}
      {job?.status === "FAILED" && (
        <span className="text-sm text-destructive">
          {job.error_message
            ? t("reports.exportFailedWithReason", { reason: job.error_message })
            : t("reports.exportFailed")}
        </span>
      )}
    </div>
  );
}
