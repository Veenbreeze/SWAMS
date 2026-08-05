import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { getOrganizations } from "@/api/endpoints/organizations";
import { getSecurityEvents } from "@/api/endpoints/securityEvents";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const EVENT_TYPES = [
  "MOCK_LOCATION_DETECTED",
  "IMPLAUSIBLE_TRAVEL_SPEED",
  "CROSS_TENANT_ACCESS_ATTEMPT",
  "ACCOUNT_LOCKED",
  "NEW_DEVICE_LOGIN",
];

const EVENT_TYPE_BADGE_VARIANT = {
  MOCK_LOCATION_DETECTED: "destructive",
  IMPLAUSIBLE_TRAVEL_SPEED: "destructive",
  CROSS_TENANT_ACCESS_ATTEMPT: "destructive",
  ACCOUNT_LOCKED: "outline",
  NEW_DEVICE_LOGIN: "secondary",
};

const selectClassName =
  "clay-inset h-8 w-full min-w-0 rounded-xl border border-transparent bg-transparent px-2.5 py-1 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

function formatTimestamp(isoString) {
  return isoString ? new Date(isoString).toLocaleString() : "—";
}

export default function SecurityEvents() {
  const { t } = useTranslation();
  const [filters, setFilters] = useState({ organization: "", event_type: "" });

  const organizationsQuery = useQuery({
    queryKey: ["organizations"],
    queryFn: () => getOrganizations(),
  });

  const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v));
  const { data, isLoading, isError } = useQuery({
    queryKey: ["security-events", filters],
    queryFn: () => getSecurityEvents(params),
  });

  const events = data?.results ?? [];
  const organizations = organizationsQuery.data?.results ?? [];

  function updateFilter(key, value) {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <h1 className="font-heading text-2xl font-semibold">{t("nav.securityEvents")}</h1>

      <div className="flex flex-wrap items-end gap-3">
        <div className="flex flex-col gap-1.5">
          <label className="text-sm text-muted-foreground">{t("nav.organizations")}</label>
          <select
            className={selectClassName}
            value={filters.organization}
            onChange={(e) => updateFilter("organization", e.target.value)}
          >
            <option value="">{t("securityEvents.filters.allOrganizations")}</option>
            {organizations.map((org) => (
              <option key={org.id} value={org.id}>
                {org.name}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm text-muted-foreground">
            {t("securityEvents.filters.eventType")}
          </label>
          <select
            className={selectClassName}
            value={filters.event_type}
            onChange={(e) => updateFilter("event_type", e.target.value)}
          >
            <option value="">{t("securityEvents.filters.allEventTypes")}</option>
            {EVENT_TYPES.map((type) => (
              <option key={type} value={type}>
                {t(`securityEventType.${type}`)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">{t("securityEvents.loading")}</p>}
      {isError && (
        <p role="alert" className="text-sm text-destructive">
          {t("securityEvents.error")}
        </p>
      )}

      {!isLoading && !isError && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t("securityEvents.table.timestamp")}</TableHead>
              <TableHead>{t("nav.organizations")}</TableHead>
              <TableHead>{t("securityEvents.table.user")}</TableHead>
              <TableHead>{t("securityEvents.table.eventType")}</TableHead>
              <TableHead>{t("securityEvents.table.description")}</TableHead>
              <TableHead>{t("securityEvents.table.ipAddress")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {events.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground">
                  {t("securityEvents.noResults")}
                </TableCell>
              </TableRow>
            )}
            {events.map((event) => (
              <TableRow key={event.id}>
                <TableCell>{formatTimestamp(event.created_at)}</TableCell>
                <TableCell>{event.organization_name ?? "—"}</TableCell>
                <TableCell>{event.user_email ?? "—"}</TableCell>
                <TableCell>
                  <Badge variant={EVENT_TYPE_BADGE_VARIANT[event.event_type] ?? "outline"}>
                    {t(`securityEventType.${event.event_type}`, { defaultValue: event.event_type })}
                  </Badge>
                </TableCell>
                <TableCell className="max-w-xs truncate">{event.description || "—"}</TableCell>
                <TableCell>{event.ip_address ?? "—"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
