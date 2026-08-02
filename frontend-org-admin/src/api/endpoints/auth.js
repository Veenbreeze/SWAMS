import apiClient from "@/api/client";

export function login({ organizationCode, identifier, password }) {
  return apiClient
    .post("/auth/login", {
      organization_code: organizationCode,
      identifier,
      password,
    })
    .then((res) => res.data);
}

export function logout(refreshToken) {
  return apiClient.post("/auth/logout", { refresh_token: refreshToken }).then((res) => res.data);
}

export function changePassword({ currentPassword, newPassword }) {
  return apiClient
    .post("/auth/change-password", {
      current_password: currentPassword,
      new_password: newPassword,
    })
    .then((res) => res.data);
}
