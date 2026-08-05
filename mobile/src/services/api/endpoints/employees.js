import apiClient from "@/services/api/client";

export function updateMyPhone({ employeeId, phone }) {
  return apiClient.patch(`/employees/${employeeId}`, { phone }).then((res) => res.data);
}

export function requestProfilePictureUpload({ employeeId, contentType, fileSize }) {
  return apiClient
    .post(`/employees/${employeeId}/profile-picture`, {
      content_type: contentType,
      file_size: fileSize,
    })
    .then((res) => res.data);
}

// Supabase's signed-upload-URL flow: PUT the raw bytes directly to the
// URL the backend just issued — this request does not go through
// `apiClient` (no JWT needed, the signed URL itself is the credential).
export async function uploadToSignedUrl({ uploadUrl, uri, contentType }) {
  const fileResponse = await fetch(uri);
  const blob = await fileResponse.blob();
  const uploadResponse = await fetch(uploadUrl, {
    method: "PUT",
    headers: { "Content-Type": contentType },
    body: blob,
  });
  if (!uploadResponse.ok) {
    throw new Error("Unable to upload the image. Please try again.");
  }
}
