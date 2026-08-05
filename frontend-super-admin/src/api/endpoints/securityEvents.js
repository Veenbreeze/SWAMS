import apiClient from "@/api/client";

export function getSecurityEvents(params) {
  return apiClient.get("/platform/security-events", { params }).then((res) => res.data);
}
