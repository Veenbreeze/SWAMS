import apiClient from "@/api/client";

export function getSuperAdminDashboard() {
  return apiClient.get("/dashboard/super-admin").then((res) => res.data);
}
