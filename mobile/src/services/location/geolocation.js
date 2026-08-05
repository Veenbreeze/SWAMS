import * as Location from "expo-location";

// Foreground-only: check-in/check-out happen at the moment the employee
// opens the app and taps a button, so background/"always" location is
// deliberately not requested (docs/01-SYSTEM-ARCHITECTURE.md scope).
export async function requestLocationPermission() {
  const { status } = await Location.requestForegroundPermissionsAsync();
  return status === "granted";
}

// expo-location's getCurrentPositionAsync has no built-in timeout — if the
// device can't get a GPS fix (indoors, poor sky view, no sensor-fusion
// support), it can hang indefinitely with no feedback, which looks
// identical to a silent failure from the user's side. This races it
// against a manual timeout so that case surfaces as a clear, actionable
// error instead.
const FIX_TIMEOUT_MS = 20000;

function withTimeout(promise, ms, message) {
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(message)), ms);
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}

export async function getCurrentPosition() {
  const position = await withTimeout(
    Location.getCurrentPositionAsync({
      // `BestForNavigation` requires additional sensor-fusion data (compass/
      // gyroscope) that not every device/fix supports, and can take far
      // longer to resolve than `High` for no benefit here — check-in only
      // needs to comfortably beat the backend's accuracy floor
      // (gps_accuracy_limit_meters, 50m by default), which `High` (accurate
      // to ~10m) already does.
      accuracy: Location.Accuracy.High,
    }),
    FIX_TIMEOUT_MS,
    "Could not get a GPS fix in time. Move to an open area, away from buildings, and try again."
  );

  return {
    latitude: position.coords.latitude,
    longitude: position.coords.longitude,
    accuracy: position.coords.accuracy,
    isMockLocation: position.mocked === true, // Android only; see Architecture §6.6
    timestamp: new Date(position.timestamp).toISOString(),
  };
}
