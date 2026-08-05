import * as Location from "expo-location";
import { getCurrentPosition } from "@/services/location/geolocation";

jest.mock("expo-location", () => ({
  Accuracy: { High: "high" },
  getCurrentPositionAsync: jest.fn(),
}));

beforeEach(() => {
  jest.clearAllMocks();
  jest.useRealTimers();
});

describe("getCurrentPosition", () => {
  it("resolves with the mapped position on a normal fix", async () => {
    Location.getCurrentPositionAsync.mockResolvedValue({
      coords: { latitude: -6.79, longitude: 39.2, accuracy: 8 },
      mocked: false,
      timestamp: 1754208000000,
    });

    const position = await getCurrentPosition();

    expect(position.latitude).toBe(-6.79);
    expect(position.accuracy).toBe(8);
    expect(position.isMockLocation).toBe(false);
    // Requests the lighter `High` accuracy tier, not the sensor-fusion-
    // dependent `BestForNavigation` one that can hang indefinitely on
    // devices without full sensor support.
    expect(Location.getCurrentPositionAsync).toHaveBeenCalledWith({ accuracy: "high" });
  });

  it("rejects with a clear message if no fix arrives before the timeout", async () => {
    jest.useFakeTimers();
    // Never resolves — simulates a GPS fix that never arrives.
    Location.getCurrentPositionAsync.mockReturnValue(new Promise(() => {}));

    const pending = getCurrentPosition();
    const assertion = expect(pending).rejects.toThrow(/GPS fix in time/);
    jest.advanceTimersByTime(20000);
    await assertion;
  });
});
