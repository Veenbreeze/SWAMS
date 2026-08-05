import apiClient from "@/api/client";

export function getLeaveTypes(params) {
  return apiClient.get("/leave/types", { params }).then((res) => res.data);
}

export function createLeaveType(data) {
  return apiClient.post("/leave/types", data).then((res) => res.data);
}

export function updateLeaveType(id, data) {
  return apiClient.patch(`/leave/types/${id}`, data).then((res) => res.data);
}

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
