import apiClient from "@/api/client";

export function getBranches(params) {
  return apiClient.get("/branches", { params }).then((res) => res.data);
}

export function createBranch(data) {
  return apiClient.post("/branches", data).then((res) => res.data);
}

export function updateBranch(id, data) {
  return apiClient.patch(`/branches/${id}`, data).then((res) => res.data);
}

export function deleteBranch(id) {
  return apiClient.delete(`/branches/${id}`).then((res) => res.data);
}

export function captureBranchLocation(id, data) {
  return apiClient.post(`/branches/${id}/capture-location`, data).then((res) => res.data);
}
