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

export function requestProfilePictureUpload({ contentType, fileSize }) {
  return apiClient
    .post("/auth/me/profile-picture", { content_type: contentType, file_size: fileSize })
    .then((res) => res.data);
}

// Supabase's signed-upload-URL flow: PUT the raw file directly to the URL
// the backend just issued — bypasses `apiClient` since the signed URL
// itself is the credential, not the session JWT.
export async function uploadToSignedUrl({ uploadUrl, file, contentType }) {
  const response = await fetch(uploadUrl, {
    method: "PUT",
    headers: { "Content-Type": contentType },
    body: file,
  });
  if (!response.ok) {
    throw new Error("Unable to upload the image. Please try again.");
  }
}
