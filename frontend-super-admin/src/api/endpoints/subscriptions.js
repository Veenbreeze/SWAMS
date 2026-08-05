import apiClient from "@/api/client";

export function getPlans() {
  return apiClient.get("/platform/subscriptions/plans").then((res) => res.data);
}

export function createPlan(data) {
  return apiClient.post("/platform/subscriptions/plans", data).then((res) => res.data);
}

export function updatePlan(planId, data) {
  return apiClient.patch(`/platform/subscriptions/plans/${planId}`, data).then((res) => res.data);
}

export function getSubscriptions(params) {
  return apiClient.get("/platform/subscriptions", { params }).then((res) => res.data);
}

export function assignSubscription(data) {
  return apiClient.post("/platform/subscriptions", data).then((res) => res.data);
}

export function cancelSubscription(subscriptionId) {
  return apiClient
    .post(`/platform/subscriptions/${subscriptionId}/cancel`)
    .then((res) => res.data);
}

export function getExpiryMonitor() {
  return apiClient.get("/platform/subscriptions/expiry-monitor").then((res) => res.data);
}
