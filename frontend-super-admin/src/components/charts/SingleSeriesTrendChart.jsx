import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

function formatDate(value) {
  return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

// A single series needs no legend box — the chart title above it names
// the series (dataviz skill's accessibility-pass rule).
export function SingleSeriesTrendChart({ data, dataKey, color = "var(--color-chart-1)" }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id={`fill-${dataKey}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.25} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
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
        <Area
          dataKey={dataKey}
          stroke={color}
          strokeWidth={2}
          strokeLinecap="round"
          fill={`url(#fill-${dataKey})`}
          dot={{ r: 3, strokeWidth: 0, fill: color }}
          activeDot={{ r: 5 }}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
