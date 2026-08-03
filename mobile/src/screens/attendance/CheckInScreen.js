import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import { checkIn, checkOut, getToday } from "@/services/api/endpoints/attendance";
import { useLocation } from "@/hooks/useLocation";

const STATUS_LABELS = {
  PRESENT: "Present",
  LATE: "Late",
  EARLY_DEPARTURE: "Early Departure",
  OVERTIME: "Overtime",
  ABSENT: "Absent",
};

function formatTime(isoString) {
  return new Date(isoString).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function CheckInScreen() {
  const { capture, isLocating } = useLocation();
  // `undefined` = still loading today's record; `null` = no record yet.
  const [today, setToday] = useState(undefined);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const loadToday = useCallback(async () => {
    try {
      setToday(await getToday());
    } catch {
      setToday(null);
    }
  }, []);

  useEffect(() => {
    loadToday();
  }, [loadToday]);

  const hasCheckedIn = Boolean(today?.check_in_time);
  const hasCheckedOut = Boolean(today?.check_out_time);

  async function handlePress() {
    setError(null);
    setIsSubmitting(true);
    try {
      const gps = await capture();
      const result = hasCheckedIn ? await checkOut(gps) : await checkIn(gps);
      setToday(result);
    } catch (err) {
      // The backend's `message` is already a human-readable default-locale
      // string (docs/03-API-SPECIFICATION.md's error envelope) — `code`
      // (e.g. OUTSIDE_GEOFENCE, MOCK_LOCATION_DETECTED, ALREADY_CHECKED_IN)
      // is there for future i18n-by-code once the app has an i18n layer.
      setError(err.message || "Unable to complete attendance action.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (today === undefined) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator />
      </View>
    );
  }

  const busy = isSubmitting || isLocating;

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Attendance</Text>

      {today && (
        <View style={styles.card}>
          <Text style={styles.status}>{STATUS_LABELS[today.status] || today.status}</Text>
          {today.branch && <Text style={styles.meta}>{today.branch.name}</Text>}
          {hasCheckedIn && (
            <Text style={styles.meta}>Checked in {formatTime(today.check_in_time)}</Text>
          )}
          {hasCheckedOut && (
            <Text style={styles.meta}>Checked out {formatTime(today.check_out_time)}</Text>
          )}
        </View>
      )}

      {error && <Text style={styles.error}>{error}</Text>}

      {!hasCheckedOut && (
        <Pressable style={styles.button} disabled={busy} onPress={handlePress}>
          {busy ? (
            <ActivityIndicator color="#ffffff" />
          ) : (
            <Text style={styles.buttonText}>{hasCheckedIn ? "Check Out" : "Check In"}</Text>
          )}
        </Pressable>
      )}

      {hasCheckedOut && <Text style={styles.done}>You&rsquo;re all done for today.</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, backgroundColor: "#ffffff" },
  centered: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#ffffff" },
  title: { fontSize: 24, fontWeight: "600", marginBottom: 24 },
  card: {
    backgroundColor: "#f9fafb",
    borderRadius: 12,
    padding: 16,
    marginBottom: 24,
  },
  status: { fontSize: 20, fontWeight: "700", color: "#111827" },
  meta: { marginTop: 4, color: "#6b7280" },
  error: { color: "#dc2626", marginBottom: 16 },
  button: {
    backgroundColor: "#111827",
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: "center",
  },
  buttonText: { color: "#ffffff", fontWeight: "600", fontSize: 16 },
  done: { color: "#059669", fontWeight: "600" },
});
