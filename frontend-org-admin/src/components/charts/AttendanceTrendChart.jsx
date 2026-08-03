import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

// present/late/absent are genuinely status states (not arbitrary
// categories), so they draw from the reserved status palette rather than
// the categorical one — see dataviz skill's color-formula.md.
const SERIES = [
  { key: "present", label: "Present", color: "var(--color-status-good)" },
  { key: "late", label: "Late", color: "var(--color-status-warning)" },
  { key: "absent", label: "Absent", color: "var(--color-status-critical)" },
];

function formatDate(value) {
  return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function AttendanceTrendChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="var(--color-chart-gridline)" vertical={false} />
        <XAxis
          dataKey="date"
          tickFormatter={formatDate}
          stroke="var(--color-chart-baseline)"
          tick={{ fill: "var(--color-muted-foreground)", fontSize: 12 }}
          tickLine={false}
        />
        <YAxis
          allowDecimals={false}
          stroke="var(--color-chart-baseline)"
          tick={{ fill: "var(--color-muted-foreground)", fontSize: 12 }}
          tickLine={false}
          axisLine={false}
          width={32}
        />
        <Tooltip
          labelFormatter={formatDate}
          contentStyle={{
            background: "var(--color-card)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-md)",
            fontSize: 12,
          }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {SERIES.map((series) => (
          <Line
            key={series.key}
            dataKey={series.key}
            name={series.label}
            stroke={series.color}
            strokeWidth={2}
            strokeLinecap="round"
            dot={{ r: 3, strokeWidth: 0, fill: series.color }}
            activeDot={{ r: 5 }}
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
