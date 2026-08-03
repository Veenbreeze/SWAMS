import { useQuery } from "@tanstack/react-query";
import { getOrgAdminDashboard } from "@/api/endpoints/dashboard";
import { AttendanceTrendChart } from "@/components/charts/AttendanceTrendChart";
import { StatusStatCard } from "@/components/charts/StatusStatCard";

export default function Dashboard() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["dashboard", "org-admin"],
    queryFn: getOrgAdminDashboard,
  });

  if (isLoading) {
    return <p className="p-6 text-sm text-muted-foreground">Loading dashboard…</p>;
  }
  if (isError) {
    return <p className="p-6 text-sm text-destructive">Unable to load the dashboard.</p>;
  }

  const { cards, trend } = data;

  return (
    <div className="flex flex-col gap-6 p-6">
      <h1 className="font-heading text-2xl font-semibold">Dashboard</h1>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatusStatCard label="Present" value={cards.present} status="good" />
        <StatusStatCard label="Late" value={cards.late} status="warning" />
        <StatusStatCard label="Absent" value={cards.absent} status="critical" />
        <StatusStatCard label="On Leave" value={cards.on_leave} status="serious" />
      </div>

      <div className="rounded-xl border bg-card p-4">
        <h2 className="mb-4 font-heading text-base font-medium">Last 7 days</h2>
        <AttendanceTrendChart data={trend} />
      </div>
    </div>
  );
}
