import apiClient from "@/api/client";

export function getLeaveRequests(params) {
  return apiClient.get("/leave/requests", { params }).then((res) => res.data);
}

export function approveLeaveRequest(id) {
  return apiClient.post(`/leave/requests/${id}/approve`).then((res) => res.data);
}

export function rejectLeaveRequest(id, reason) {
  return apiClient.post(`/leave/requests/${id}/reject`, { reason }).then((res) => res.data);
}

export function getLeaveBalance(employeeId) {
  return apiClient
    .get("/leave/balance", { params: employeeId ? { employee_id: employeeId } : undefined })
    .then((res) => res.data);
}
