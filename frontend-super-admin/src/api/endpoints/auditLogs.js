import apiClient from "@/api/client";

export function getAuditLogs(params) {
  return apiClient.get("/platform/audit-logs", { params }).then((res) => res.data);
}
