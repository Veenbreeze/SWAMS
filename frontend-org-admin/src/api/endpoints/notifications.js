import apiClient from "@/api/client";

export function getNotifications(params) {
  return apiClient.get("/notifications", { params }).then((res) => res.data);
}

export function markNotificationRead(id) {
  return apiClient.post(`/notifications/${id}/read`).then((res) => res.data);
}

export function markAllNotificationsRead() {
  return apiClient.post("/notifications/read-all").then((res) => res.data);
}
