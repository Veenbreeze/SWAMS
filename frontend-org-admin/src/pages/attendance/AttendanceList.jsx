import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { getAttendanceRecords } from "@/api/endpoints/attendance";
import { getBranches } from "@/api/endpoints/branches";
import { getDepartments } from "@/api/endpoints/departments";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const STATUS_OPTIONS = ["PRESENT", "LATE", "EARLY_DEPARTURE", "OVERTIME", "ABSENT"];
const STATUS_BADGE_VARIANT = {
  PRESENT: "default",
  LATE: "destructive",
  EARLY_DEPARTURE: "destructive",
  OVERTIME: "outline",
  ABSENT: "secondary",
};

const selectClassName =
  "clay-inset h-8 w-full min-w-0 rounded-xl border border-transparent bg-transparent px-2.5 py-1 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

function formatTime(isoString) {
  return isoString ? new Date(isoString).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—";
}

export default function AttendanceList() {
  const { t } = useTranslation();
  const [filters, setFilters] = useState({
    attendance_date: "",
    status: "",
    branch: "",
    employee__department: "",
  });

  const branchesQuery = useQuery({ queryKey: ["branches"], queryFn: () => getBranches() });
  const departmentsQuery = useQuery({ queryKey: ["departments"], queryFn: () => getDepartments() });

  const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v));
  const { data, isLoading, isError } = useQuery({
    queryKey: ["attendance", filters],
    queryFn: () => getAttendanceRecords(params),
  });

  const records = data?.results ?? [];
  const branches = branchesQuery.data?.results ?? [];
  const departments = departmentsQuery.data?.results ?? [];

  function updateFilter(key, value) {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <h1 className="font-heading text-2xl font-semibold">{t("nav.attendance")}</h1>

      <div className="flex flex-wrap items-end gap-3">
        <div className="flex flex-col gap-1.5">
          <label className="text-sm text-muted-foreground">{t("attendance.filters.date")}</label>
          <Input
            type="date"
            value={filters.attendance_date}
            onChange={(e) => updateFilter("attendance_date", e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm text-muted-foreground">{t("attendance.filters.status")}</label>
          <select
            className={selectClassName}
            value={filters.status}
            onChange={(e) => updateFilter("status", e.target.value)}
          >
            <option value="">{t("attendance.filters.allStatuses")}</option>
            {STATUS_OPTIONS.map((status) => (
              <option key={status} value={status}>
                {t(`attendanceStatus.${status}`)}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm text-muted-foreground">{t("nav.branches")}</label>
          <select
            className={selectClassName}
            value={filters.branch}
            onChange={(e) => updateFilter("branch", e.target.value)}
          >
            <option value="">{t("attendance.filters.allBranches")}</option>
            {branches.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm text-muted-foreground">{t("nav.departments")}</label>
          <select
            className={selectClassName}
            value={filters.employee__department}
            onChange={(e) => updateFilter("employee__department", e.target.value)}
          >
            <option value="">{t("attendance.filters.allDepartments")}</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">{t("attendance.loading")}</p>}
      {isError && (
        <p role="alert" className="text-sm text-destructive">
          {t("attendance.error")}
        </p>
      )}

      {!isLoading && !isError && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t("attendance.table.employee")}</TableHead>
              <TableHead>{t("attendance.table.branch")}</TableHead>
              <TableHead>{t("attendance.table.date")}</TableHead>
              <TableHead>{t("attendance.table.checkIn")}</TableHead>
              <TableHead>{t("attendance.table.checkOut")}</TableHead>
              <TableHead>{t("attendance.table.status")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {records.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground">
                  {t("attendance.noResults")}
                </TableCell>
              </TableRow>
            )}
            {records.map((record) => (
              <TableRow key={record.id}>
                <TableCell>{record.employee_name}</TableCell>
                <TableCell>{record.branch?.name ?? "—"}</TableCell>
                <TableCell>{record.attendance_date}</TableCell>
                <TableCell>{formatTime(record.check_in_time)}</TableCell>
                <TableCell>{formatTime(record.check_out_time)}</TableCell>
                <TableCell>
                  <Badge variant={STATUS_BADGE_VARIANT[record.status] ?? "outline"}>
                    {t(`attendanceStatus.${record.status}`, { defaultValue: record.status })}
                  </Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
