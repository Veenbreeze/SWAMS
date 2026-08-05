import apiClient from "@/services/api/client";

export function getUnreadCount() {
  return apiClient
    .get("/notifications", { params: { is_read: false, page_size: 1 } })
    .then((res) => res.data.count);
}

export function getNotifications(params) {
  return apiClient.get("/notifications", { params }).then((res) => res.data);
}

export function markNotificationRead(id) {
  return apiClient.post(`/notifications/${id}/read`).then((res) => res.data);
}
