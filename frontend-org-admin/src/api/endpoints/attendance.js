import apiClient from "@/api/client";

export function getAttendanceRecords(params) {
  return apiClient.get("/attendance", { params }).then((res) => res.data);
}

export function getShifts() {
  return apiClient.get("/shifts").then((res) => res.data);
}

export function createShift(data) {
  return apiClient.post("/shifts", data).then((res) => res.data);
}

export function updateShift(id, data) {
  return apiClient.patch(`/shifts/${id}`, data).then((res) => res.data);
}

export function deleteShift(id) {
  return apiClient.delete(`/shifts/${id}`).then((res) => res.data);
}

export function getAttendanceRule() {
  return apiClient.get("/attendance-rule").then((res) => res.data);
}

export function updateAttendanceRule(data) {
  return apiClient.patch("/attendance-rule", data).then((res) => res.data);
}
