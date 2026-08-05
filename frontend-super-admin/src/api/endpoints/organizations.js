import apiClient from "@/api/client";

export function getOrganizations(params) {
  return apiClient.get("/platform/organizations", { params }).then((res) => res.data);
}

export function createOrganization(data) {
  return apiClient.post("/platform/organizations", data).then((res) => res.data);
}

export function updateOrganization(id, data) {
  return apiClient.patch(`/platform/organizations/${id}`, data).then((res) => res.data);
}

export function suspendOrganization(id) {
  return apiClient.post(`/platform/organizations/${id}/suspend`).then((res) => res.data);
}

export function activateOrganization(id) {
  return apiClient.post(`/platform/organizations/${id}/activate`).then((res) => res.data);
}
