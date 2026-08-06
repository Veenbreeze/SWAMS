import { useCallback, useState } from "react";

// Browser Geolocation API — used for the "capture current location" step
// when creating/relocating a Branch. The backend's `gps_accuracy` field on
// create/capture-location exists specifically as proof of a real GPS read
// (not free-typed coordinates), so this hook is how the admin UI produces
// that reading rather than asking them to type it.
//
// Mobile browsers refuse Geolocation entirely on an insecure origin (plain
// http://, other than localhost) — checked explicitly here for a clear
// message, rather than relying on each browser's own (often cryptic) error
// text for that specific case.
const GEO_ERROR_MESSAGES = {
  1: "Location permission was denied. Enable it in your browser's site settings and try again.",
  2: "Your device could not determine its location. Move to an open area and try again.",
  3: "Location request timed out. Move to an open area, away from buildings, and try again.",
};

export function useBrowserLocation() {
  const [isLocating, setIsLocating] = useState(false);
  const [error, setError] = useState(null);

  const capture = useCallback(() => {
    setError(null);
    setIsLocating(true);
    return new Promise((resolve, reject) => {
      if (!window.isSecureContext) {
        const err = new Error(
          "Location capture requires a secure (https://) connection. Open this site over HTTPS and try again."
        );
        setError(err.message);
        setIsLocating(false);
        reject(err);
        return;
      }
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
            // The browser's raw float64 coords carry far more than 6
            // decimal places (e.g. -6.79235412345678) — the backend's
            // DecimalField(max_digits=9, decimal_places=6) rejects that
            // outright rather than rounding it, surfacing as "no more
            // than 6 digits". Round here to match: 6 decimal places is
            // already ~11cm of precision at the equator, far finer than
            // GPS hardware itself resolves.
            latitude: Number(position.coords.latitude.toFixed(6)),
            longitude: Number(position.coords.longitude.toFixed(6)),
            gps_accuracy: position.coords.accuracy,
          });
        },
        (geoError) => {
          setIsLocating(false);
          const message = GEO_ERROR_MESSAGES[geoError.code] || geoError.message;
          setError(message);
          reject(new Error(message));
        },
        { enableHighAccuracy: true, timeout: 15000 }
      );
    });
  }, []);

  return { capture, isLocating, error };
}
