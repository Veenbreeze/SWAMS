import { useCallback, useState } from "react";

// Browser Geolocation API — used for the "capture current location" step
// when creating/relocating a Branch. The backend's `gps_accuracy` field on
// create/capture-location exists specifically as proof of a real GPS read
// (not free-typed coordinates), so this hook is how the admin UI produces
// that reading rather than asking them to type it.
export function useBrowserLocation() {
  const [isLocating, setIsLocating] = useState(false);
  const [error, setError] = useState(null);

  const capture = useCallback(() => {
    setError(null);
    setIsLocating(true);
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        const err = new Error("Geolocation is not available in this browser.");
        setError(err.message);
        setIsLocating(false);
        reject(err);
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setIsLocating(false);
          resolve({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            gps_accuracy: position.coords.accuracy,
          });
        },
        (geoError) => {
          setIsLocating(false);
          setError(geoError.message);
          reject(geoError);
        },
        { enableHighAccuracy: true, timeout: 15000 }
      );
    });
  }, []);

  return { capture, isLocating, error };
}
