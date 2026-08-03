import { useCallback, useState } from "react";
import { getCurrentPosition, requestLocationPermission } from "@/services/location/geolocation";

export function useLocation() {
  const [isLocating, setIsLocating] = useState(false);

  const capture = useCallback(async () => {
    setIsLocating(true);
    try {
      const granted = await requestLocationPermission();
      if (!granted) {
        throw new Error("Location permission is required to check in.");
      }
      return await getCurrentPosition();
    } finally {
      setIsLocating(false);
    }
  }, []);

  return { capture, isLocating };
}
