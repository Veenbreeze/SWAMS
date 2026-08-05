import apiClient from "@/api/client";

export function getEmployees(params) {
  return apiClient.get("/employees", { params }).then((res) => res.data);
}

export function createEmployee(data) {
  return apiClient.post("/employees", data).then((res) => res.data);
}

export function updateEmployee(id, data) {
  return apiClient.patch(`/employees/${id}`, data).then((res) => res.data);
}

export function terminateEmployee(id) {
  return apiClient.delete(`/employees/${id}`).then((res) => res.data);
}

export function resetEmployeePassword(id) {
  return apiClient.post(`/employees/${id}/reset-password`).then((res) => res.data);
}
