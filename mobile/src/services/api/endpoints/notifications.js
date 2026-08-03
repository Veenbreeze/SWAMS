import apiClient from "@/services/api/client";

export function getUnreadCount() {
  return apiClient
    .get("/notifications", { params: { is_read: false, page_size: 1 } })
    .then((res) => res.data.count);
}
