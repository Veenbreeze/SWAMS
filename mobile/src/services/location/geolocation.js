import * as Location from "expo-location";

// Foreground-only: check-in/check-out happen at the moment the employee
// opens the app and taps a button, so background/"always" location is
// deliberately not requested (docs/01-SYSTEM-ARCHITECTURE.md scope).
export async function requestLocationPermission() {
  const { status } = await Location.requestForegroundPermissionsAsync();
  return status === "granted";
}

export async function getCurrentPosition() {
  const position = await Location.getCurrentPositionAsync({
    accuracy: Location.Accuracy.BestForNavigation,
  });

  return {
    latitude: position.coords.latitude,
    longitude: position.coords.longitude,
    accuracy: position.coords.accuracy,
    isMockLocation: position.mocked === true, // Android only; see Architecture §6.6
    timestamp: new Date(position.timestamp).toISOString(),
  };
}
