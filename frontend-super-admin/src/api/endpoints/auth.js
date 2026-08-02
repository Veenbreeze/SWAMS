import apiClient from "@/api/client";

// Super Admin accounts are platform-wide (organization_id IS NULL), so no
// organization_code is sent here — see docs/03-API-SPECIFICATION.md §1.
export function login({ identifier, password }) {
  return apiClient.post("/auth/login", { identifier, password }).then((res) => res.data);
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
