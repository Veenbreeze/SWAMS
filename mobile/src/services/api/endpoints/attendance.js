import apiClient from "@/services/api/client";

// `gps` is the shape returned by services/location/geolocation.js's
// getCurrentPosition(): { latitude, longitude, accuracy, isMockLocation }.
function toCheckPayload(gps, deviceId) {
  return {
    latitude: gps.latitude,
    longitude: gps.longitude,
    accuracy: gps.accuracy,
    is_mock_location: gps.isMockLocation,
    device_id: deviceId,
    client_timestamp: new Date().toISOString(),
  };
}

export function checkIn(gps, deviceId) {
  return apiClient.post("/attendance/check-in", toCheckPayload(gps, deviceId)).then((res) => res.data);
}

export function checkOut(gps, deviceId) {
  return apiClient
    .post("/attendance/check-out", toCheckPayload(gps, deviceId))
    .then((res) => res.data);
}

export function getToday() {
  return apiClient.get("/attendance/today").then((res) => (res.status === 204 ? null : res.data));
}

// `pageUrl`, when given, is the exact `next`/`previous` URL DRF's cursor
// pagination returned from a prior call — axios treats an absolute URL as
// absolute (ignoring `baseURL`), so passing it straight through here is
// simpler and less error-prone than re-parsing the opaque cursor token out
// of it ourselves.
export function getHistory(pageUrl) {
  return apiClient.get(pageUrl || "/attendance/history").then((res) => res.data);
}
