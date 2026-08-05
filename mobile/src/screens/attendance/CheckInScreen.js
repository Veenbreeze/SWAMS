import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { checkIn, checkOut, getHistory, getToday } from "@/services/api/endpoints/attendance";
import { useLocation } from "@/hooks/useLocation";
import { useI18n } from "@/i18n";
import { colors, statusColors } from "@/theme/colors";
import { clayRadius } from "@/theme/clay";
import { ClaySurface, ClayButton } from "@/components/clay";

function formatTime(isoString) {
  return new Date(isoString).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatDuration(minutes) {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
}

function daysAgo(count) {
  const date = new Date();
  date.setDate(date.getDate() - count);
  date.setHours(0, 0, 0, 0);
  return date;
}

export default function CheckInScreen({ navigation }) {
  const { t } = useI18n();
  const { capture, isLocating } = useLocation();
  // `undefined` = still loading today's record; `null` = no record yet.
  const [today, setToday] = useState(undefined);
  const [weekSummary, setWeekSummary] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const loadToday = useCallback(async () => {
    try {
      setToday(await getToday());
    } catch {
      setToday(null);
    }

    try {
      const history = await getHistory();
      const cutoff = daysAgo(6);
      const tally = {};
      for (const record of history.results) {
        if (new Date(record.attendance_date) < cutoff) continue;
        tally[record.status] = (tally[record.status] ?? 0) + 1;
      }
      setWeekSummary(tally);
    } catch {
      setWeekSummary({});
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
      setError(err.message || t("checkIn.genericError"));
    } finally {
      setIsSubmitting(false);
    }
  }

  if (today === undefined) {
    return (
      <SafeAreaView style={styles.centered} edges={["top"]}>
        <ActivityIndicator />
      </SafeAreaView>
    );
  }

  const busy = isSubmitting || isLocating;
  const weekEntries = Object.entries(weekSummary);

  return (
    <SafeAreaView style={styles.safeArea} edges={["top"]}>
      <View style={styles.container}>
        <View style={styles.headerRow}>
          <Text style={styles.title}>{t("checkIn.title")}</Text>
          <Pressable style={styles.historyLink} onPress={() => navigation.navigate("History")}>
            <Text style={styles.historyLinkText}>{t("checkIn.viewHistory")}</Text>
            <Ionicons name="chevron-forward" size={16} color={colors.primary} />
          </Pressable>
        </View>

        {today && (
          <ClaySurface radius={clayRadius.lg} contentStyle={styles.cardContent} style={styles.cardWrapper}>
            <View style={styles.statusRow}>
              <View
                style={[
                  styles.statusDot,
                  { backgroundColor: statusColors[today.status] ?? colors.textMuted },
                ]}
              />
              <Text style={styles.status}>
                {t(`attendanceStatus.${today.status}`, { defaultValue: today.status })}
              </Text>
            </View>
            {today.branch && <Text style={styles.meta}>{today.branch.name}</Text>}

            {hasCheckedIn && (
              <View style={styles.punctualityRow}>
                <Text style={styles.meta}>
                  {t("checkIn.checkedIn", { time: formatTime(today.check_in_time) })}
                </Text>
                <PunctualityBadge
                  isGood={!(today.late_minutes > 0)}
                  goodLabel={t("checkIn.onTime")}
                  badLabel={t("checkIn.lateBy", { duration: formatDuration(today.late_minutes) })}
                  badColor={statusColors.LATE}
                />
              </View>
            )}

            {hasCheckedOut && (
              <View style={styles.punctualityRow}>
                <Text style={styles.meta}>
                  {t("checkIn.checkedOut", { time: formatTime(today.check_out_time) })}
                </Text>
                {today.early_departure_minutes > 0 ? (
                  <PunctualityBadge
                    isGood={false}
                    badLabel={t("checkIn.leftEarlyBy", {
                      duration: formatDuration(today.early_departure_minutes),
                    })}
                    badColor={statusColors.EARLY_DEPARTURE}
                  />
                ) : today.overtime_minutes > 0 ? (
                  <PunctualityBadge
                    isGood={false}
                    badLabel={t("checkIn.overtimeBy", {
                      duration: formatDuration(today.overtime_minutes),
                    })}
                    badColor={colors.secondary}
                  />
                ) : (
                  <PunctualityBadge isGood goodLabel={t("checkIn.leftOnTime")} />
                )}
              </View>
            )}

            {typeof today.working_minutes === "number" && today.working_minutes > 0 && (
              <Text style={styles.meta}>
                {t("checkIn.hoursWorked", { duration: formatDuration(today.working_minutes) })}
              </Text>
            )}
          </ClaySurface>
        )}

        {weekEntries.length > 0 && (
          <ClaySurface radius={clayRadius.lg} contentStyle={styles.cardContent} style={styles.cardWrapper}>
            <Text style={styles.cardLabel}>{t("checkIn.thisWeek")}</Text>
            <View style={styles.weekRow}>
              {weekEntries.map(([status, count]) => (
                <View key={status} style={styles.weekStat}>
                  <View
                    style={[
                      styles.statusDot,
                      { backgroundColor: statusColors[status] ?? colors.textMuted },
                    ]}
                  />
                  <Text style={styles.weekStatCount}>{count}</Text>
                  <Text style={styles.weekStatLabel}>
                    {t(`attendanceStatus.${status}`, { defaultValue: status })}
                  </Text>
                </View>
              ))}
            </View>
          </ClaySurface>
        )}

        {error && <Text style={styles.error}>{error}</Text>}

        {!hasCheckedOut && (
          <ClayButton
            title={hasCheckedIn ? t("checkIn.checkOut") : t("checkIn.checkIn")}
            onPress={handlePress}
            loading={busy}
          />
        )}

        {hasCheckedOut && <Text style={styles.done}>{t("checkIn.allDone")}</Text>}
      </View>
    </SafeAreaView>
  );
}

function PunctualityBadge({ isGood, goodLabel, badLabel, badColor }) {
  const color = isGood ? colors.success : badColor;
  return (
    <View style={[styles.badge, { backgroundColor: `${color}1a` }]}>
      <Text style={[styles.badgeText, { color }]}>{isGood ? goodLabel : badLabel}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: colors.background },
  container: { flex: 1, padding: 24, backgroundColor: colors.background },
  centered: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: colors.background },
  headerRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 24,
  },
  title: { fontSize: 24, fontWeight: "600" },
  historyLink: { flexDirection: "row", alignItems: "center", gap: 2 },
  historyLinkText: { color: colors.primary, fontWeight: "600", fontSize: 13 },
  cardWrapper: { marginBottom: 20 },
  cardContent: { padding: 16 },
  cardLabel: { color: "#6b7280", marginBottom: 10 },
  statusRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  statusDot: { width: 8, height: 8, borderRadius: 4 },
  status: { fontSize: 20, fontWeight: "700", color: "#111827" },
  meta: { marginTop: 4, color: "#6b7280" },
  punctualityRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 4,
  },
  badge: { borderRadius: 999, paddingHorizontal: 10, paddingVertical: 4 },
  badgeText: { fontSize: 12, fontWeight: "700" },
  weekRow: { flexDirection: "row", flexWrap: "wrap", gap: 20 },
  weekStat: { alignItems: "center", minWidth: 56 },
  weekStatCount: { fontSize: 20, fontWeight: "700", color: "#111827", marginTop: 4 },
  weekStatLabel: { fontSize: 11, color: "#6b7280", marginTop: 2 },
  error: { color: "#dc2626", marginBottom: 16 },
  done: { color: "#059669", fontWeight: "600" },
});
