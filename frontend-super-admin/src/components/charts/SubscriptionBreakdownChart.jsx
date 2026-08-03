import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

// Subscription status genuinely is a status (not an arbitrary category),
// so it draws from the reserved status palette — see dataviz skill's
// color-formula.md. Direct Y-axis labels mean identity is never
// color-alone even though there's no legend box.
const STATUS_COLOR = {
  ACTIVE: "var(--color-status-good)",
  TRIAL: "var(--color-status-warning)",
  EXPIRED: "var(--color-status-critical)",
  CANCELLED: "var(--color-status-serious)",
  NONE: "var(--color-muted-foreground)",
};

const STATUS_LABEL = {
  ACTIVE: "Active",
  TRIAL: "Trial",
  EXPIRED: "Expired",
  CANCELLED: "Cancelled",
  NONE: "No subscription",
};

export function SubscriptionBreakdownChart({ breakdown }) {
  const data = Object.entries(breakdown)
    .map(([status, count]) => ({ status, label: STATUS_LABEL[status] ?? status, count }))
    .sort((a, b) => b.count - a.count);

  return (
    <ResponsiveContainer width="100%" height={Math.max(160, data.length * 44)}>
      <BarChart data={data} layout="vertical" margin={{ top: 8, right: 24, left: 8, bottom: 0 }}>
        <XAxis type="number" allowDecimals={false} hide />
        <YAxis
          type="category"
          dataKey="label"
          width={110}
          tickLine={false}
          axisLine={false}
          tick={{ fill: "var(--color-foreground)", fontSize: 13 }}
        />
        <Tooltip
          contentStyle={{
            background: "var(--color-card)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-md)",
            fontSize: 12,
          }}
        />
        <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={20} isAnimationActive={false}>
          {data.map((entry) => (
            <Cell key={entry.status} fill={STATUS_COLOR[entry.status] ?? "var(--color-chart-1)"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
