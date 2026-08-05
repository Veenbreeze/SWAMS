import { renderHook, act } from "@testing-library/react-native";
import { useLocation } from "@/hooks/useLocation";

jest.mock("@/services/location/geolocation", () => ({
  requestLocationPermission: jest.fn(),
  getCurrentPosition: jest.fn(),
}));

const geolocation = require("@/services/location/geolocation");

beforeEach(() => {
  jest.clearAllMocks();
});

describe("useLocation", () => {
  it("rejects with a clear error when permission is denied", async () => {
    geolocation.requestLocationPermission.mockResolvedValue(false);
    const { result } = await renderHook(() => useLocation());

    let error;
    await act(async () => {
      try {
        await result.current.capture();
      } catch (err) {
        error = err;
      }
    });

    expect(error.message).toBe("Location permission is required to check in.");
    expect(geolocation.getCurrentPosition).not.toHaveBeenCalled();
    expect(result.current.isLocating).toBe(false);
  });

  it("returns the captured position once permission is granted", async () => {
    geolocation.requestLocationPermission.mockResolvedValue(true);
    geolocation.getCurrentPosition.mockResolvedValue({
      latitude: -6.79,
      longitude: 39.2,
      accuracy: 5,
      isMockLocation: false,
      timestamp: "2026-08-03T08:00:00.000Z",
    });
    const { result } = await renderHook(() => useLocation());

    let position;
    await act(async () => {
      position = await result.current.capture();
    });

    expect(position.latitude).toBe(-6.79);
    expect(result.current.isLocating).toBe(false);
  });

  it("resets isLocating even when capture fails", async () => {
    geolocation.requestLocationPermission.mockResolvedValue(true);
    geolocation.getCurrentPosition.mockRejectedValue(new Error("GPS unavailable"));
    const { result } = await renderHook(() => useLocation());

    let error;
    await act(async () => {
      try {
        await result.current.capture();
      } catch (err) {
        error = err;
      }
    });

    expect(error.message).toBe("GPS unavailable");
    expect(result.current.isLocating).toBe(false);
  });
});
