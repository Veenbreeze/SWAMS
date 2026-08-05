import apiClient from "@/api/client";

export function getRecommendations(params) {
  return apiClient.get("/recommendations", { params }).then((res) => res.data);
}
