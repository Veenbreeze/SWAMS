import apiClient from "@/api/client";

export function getPlatformSettings() {
  return apiClient.get("/platform/settings").then((res) => res.data);
}

export function updatePlatformSettings(data) {
  return apiClient.patch("/platform/settings", data).then((res) => res.data);
}
