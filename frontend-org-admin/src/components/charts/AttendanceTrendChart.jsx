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
import { useTranslation } from "react-i18next";

function formatDate(value) {
  return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function AttendanceTrendChart({ data }) {
  const { t } = useTranslation();

  // present/late/absent are genuinely status states (not arbitrary
  // categories), so they draw from the reserved status palette rather than
  // the categorical one — see dataviz skill's color-formula.md.
  const series = [
    { key: "present", label: t("attendanceChart.present"), color: "var(--color-status-good)" },
    { key: "late", label: t("attendanceChart.late"), color: "var(--color-status-warning)" },
    { key: "absent", label: t("attendanceChart.absent"), color: "var(--color-status-critical)" },
  ];

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
        {series.map((s) => (
          <Line
            key={s.key}
            dataKey={s.key}
            name={s.label}
            stroke={s.color}
            strokeWidth={2}
            strokeLinecap="round"
            dot={{ r: 3, strokeWidth: 0, fill: s.color }}
            activeDot={{ r: 5 }}
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
