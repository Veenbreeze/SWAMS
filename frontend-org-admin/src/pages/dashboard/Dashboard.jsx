import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { getOrgAdminDashboard } from "@/api/endpoints/dashboard";
import { AttendanceTrendChart } from "@/components/charts/AttendanceTrendChart";
import { StatusStatCard } from "@/components/charts/StatusStatCard";

export default function Dashboard() {
  const { t } = useTranslation();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["dashboard", "org-admin"],
    queryFn: getOrgAdminDashboard,
  });

  if (isLoading) {
    return <p className="p-6 text-sm text-muted-foreground">{t("dashboard.loading")}</p>;
  }
  if (isError) {
    return (
      <p role="alert" className="p-6 text-sm text-destructive">
        {t("dashboard.error")}
      </p>
    );
  }

  const { cards, trend } = data;

  return (
    <div className="flex flex-col gap-6 p-6">
      <h1 className="font-heading text-2xl font-semibold">{t("dashboard.title")}</h1>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatusStatCard label={t("dashboard.present")} value={cards.present} status="good" />
        <StatusStatCard label={t("dashboard.late")} value={cards.late} status="warning" />
        <StatusStatCard label={t("dashboard.absent")} value={cards.absent} status="critical" />
        <StatusStatCard label={t("dashboard.onLeave")} value={cards.on_leave} status="serious" />
      </div>

      <div className="rounded-xl border bg-card p-4">
        <h2 className="mb-4 font-heading text-base font-medium">{t("dashboard.last7Days")}</h2>
        <AttendanceTrendChart data={trend} />
      </div>
    </div>
  );
}
