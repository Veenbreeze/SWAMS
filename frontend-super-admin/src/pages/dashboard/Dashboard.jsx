import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { getSuperAdminDashboard } from "@/api/endpoints/dashboard";
import { SingleSeriesTrendChart } from "@/components/charts/SingleSeriesTrendChart";
import { StatCard } from "@/components/charts/StatCard";
import { SubscriptionBreakdownChart } from "@/components/charts/SubscriptionBreakdownChart";

// The backend reports new-organizations-per-day; "growth" reads as a
// running total over time, not a per-day count, so the cumulative sum is
// computed here rather than duplicating this trivial transform server-side.
function toCumulative(series) {
  let total = 0;
  return series.map((point) => {
    total += point.count;
    return { date: point.date, total };
  });
}

export default function Dashboard() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["dashboard", "super-admin"],
    queryFn: getSuperAdminDashboard,
  });

  const growth = useMemo(() => (data ? toCumulative(data.organization_growth) : []), [data]);

  if (isLoading) {
    return <p className="p-6 text-sm text-muted-foreground">Loading platform dashboard…</p>;
  }
  if (isError) {
    return <p className="p-6 text-sm text-destructive">Unable to load the platform dashboard.</p>;
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <h1 className="font-heading text-2xl font-semibold">Platform Dashboard</h1>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Total Organizations" value={data.total_organizations} />
        <StatCard label="Active" value={data.active_organizations} status="good" />
        <StatCard label="Trial" value={data.trial_organizations} status="warning" />
        <StatCard label="Suspended" value={data.suspended_organizations} status="critical" />
        <StatCard label="Expired Subscriptions" value={data.expired_subscriptions} status="critical" />
        <StatCard label="Total Users" value={data.total_users} />
        <StatCard label="New (30 days)" value={data.new_organizations_last_30_days} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border bg-card p-4">
          <h2 className="mb-4 font-heading text-base font-medium">Organization growth (30 days)</h2>
          <SingleSeriesTrendChart data={growth} dataKey="total" color="var(--color-chart-1)" />
        </div>

        <div className="rounded-xl border bg-card p-4">
          <h2 className="mb-4 font-heading text-base font-medium">Subscription status</h2>
          <SubscriptionBreakdownChart breakdown={data.subscription_breakdown} />
        </div>

        <div className="rounded-xl border bg-card p-4 lg:col-span-2">
          <h2 className="mb-4 font-heading text-base font-medium">System activity (7 days)</h2>
          <SingleSeriesTrendChart
            data={data.system_activity}
            dataKey="count"
            color="var(--color-chart-2)"
          />
        </div>
      </div>
    </div>
  );
}
