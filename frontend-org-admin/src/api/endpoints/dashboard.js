import apiClient from "@/api/client";

export function getOrgAdminDashboard() {
  return apiClient.get("/dashboard/org-admin").then((res) => res.data);
}
