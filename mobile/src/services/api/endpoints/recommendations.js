import apiClient from "@/services/api/client";

export function submitRecommendation(message) {
  return apiClient.post("/recommendations", { message }).then((res) => res.data);
}
