// Status colors ship with an icon + label, never color alone (dataviz
// skill's status-palette rule) — the dot pairs with the text label here
// rather than color-coding the number itself.
const STATUS_DOT_CLASS = {
  good: "bg-status-good",
  warning: "bg-status-warning",
  serious: "bg-status-serious",
  critical: "bg-status-critical",
};

export function StatusStatCard({ label, value, status }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border bg-card p-4">
      <span
        aria-hidden="true"
        className={`size-2.5 shrink-0 rounded-full ${STATUS_DOT_CLASS[status] ?? "bg-muted-foreground"}`}
      />
      <div>
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="text-2xl font-semibold tabular-nums">{value ?? "—"}</p>
      </div>
    </div>
  );
}
