import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { getAuditLogs } from "@/api/endpoints/auditLogs";
import { getOrganizations } from "@/api/endpoints/organizations";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const selectClassName =
  "clay-inset h-8 w-full min-w-0 rounded-xl border border-transparent bg-transparent px-2.5 py-1 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

function formatTimestamp(isoString) {
  return isoString ? new Date(isoString).toLocaleString() : "—";
}

export default function AuditLogViewer() {
  const { t } = useTranslation();
  const [filters, setFilters] = useState({ organization: "", action: "" });

  const organizationsQuery = useQuery({
    queryKey: ["organizations"],
    queryFn: () => getOrganizations(),
  });

  const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v));
  const { data, isLoading, isError } = useQuery({
    queryKey: ["audit-logs", filters],
    queryFn: () => getAuditLogs(params),
  });

  const logs = data?.results ?? [];
  const organizations = organizationsQuery.data?.results ?? [];

  function updateFilter(key, value) {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <h1 className="font-heading text-2xl font-semibold">{t("nav.auditLogs")}</h1>

      <div className="flex flex-wrap items-end gap-3">
        <div className="flex flex-col gap-1.5">
          <label className="text-sm text-muted-foreground">{t("nav.organizations")}</label>
          <select
            className={selectClassName}
            value={filters.organization}
            onChange={(e) => updateFilter("organization", e.target.value)}
          >
            <option value="">{t("auditLogs.filters.allOrganizations")}</option>
            {organizations.map((org) => (
              <option key={org.id} value={org.id}>
                {org.name}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm text-muted-foreground">{t("auditLogs.filters.action")}</label>
          <Input
            value={filters.action}
            onChange={(e) => updateFilter("action", e.target.value)}
            placeholder={t("auditLogs.filters.actionPlaceholder")}
          />
        </div>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">{t("auditLogs.loading")}</p>}
      {isError && (
        <p role="alert" className="text-sm text-destructive">
          {t("auditLogs.error")}
        </p>
      )}

      {!isLoading && !isError && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t("auditLogs.table.timestamp")}</TableHead>
              <TableHead>{t("nav.organizations")}</TableHead>
              <TableHead>{t("auditLogs.table.user")}</TableHead>
              <TableHead>{t("auditLogs.table.action")}</TableHead>
              <TableHead>{t("auditLogs.table.description")}</TableHead>
              <TableHead>{t("auditLogs.table.ipAddress")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {logs.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground">
                  {t("auditLogs.noResults")}
                </TableCell>
              </TableRow>
            )}
            {logs.map((log) => (
              <TableRow key={log.id}>
                <TableCell>{formatTimestamp(log.timestamp)}</TableCell>
                <TableCell>{log.organization_name ?? "—"}</TableCell>
                <TableCell>{log.user_email ?? "—"}</TableCell>
                <TableCell>{log.action}</TableCell>
                <TableCell className="max-w-xs truncate">{log.description || "—"}</TableCell>
                <TableCell>{log.ip_address ?? "—"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
