import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { getLeaveBalance, getLeaveRequests } from "@/services/api/endpoints/leave";
import { useI18n } from "@/i18n";
import { colors, statusColors } from "@/theme/colors";
import { clayRadius } from "@/theme/clay";
import { ClaySurface, ClayButton } from "@/components/clay";

function formatDate(isoDate) {
  return new Date(isoDate).toLocaleDateString([], { month: "short", day: "numeric" });
}

export default function LeaveHistoryScreen({ navigation }) {
  const { t } = useI18n();
  const [requests, setRequests] = useState(undefined);
  const [balance, setBalance] = useState([]);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      const [requestsData, balanceData] = await Promise.all([
        getLeaveRequests(),
        getLeaveBalance().catch(() => ({ results: [] })),
      ]);
      setRequests(requestsData.results);
      setBalance(balanceData.results ?? []);
    } catch (err) {
      setError(err.message || t("leave.history.genericError"));
      setRequests([]);
    }
  }, [t]);

  useEffect(() => {
    load();
  }, [load]);

  if (requests === undefined) {
    return (
      <SafeAreaView style={styles.centered} edges={["top"]}>
        <ActivityIndicator />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safeArea} edges={["top"]}>
      <FlatList
        style={styles.container}
        data={requests}
        keyExtractor={(item) => item.id}
        ListHeaderComponent={
          <>
            <View style={styles.headerRow}>
              <Text style={styles.title}>{t("nav.leaveHistory")}</Text>
              <ClayButton
                title={t("leave.history.addLeave")}
                radius={clayRadius.pill}
                compact
                onPress={() => navigation.navigate("LeaveRequest")}
                icon={<Ionicons name="add" size={16} color="#ffffff" />}
              />
            </View>
            <View style={styles.balanceRow}>
              {balance.map((entry) => (
                <ClaySurface
                  key={entry.id}
                  radius={clayRadius.sm}
                  subtle
                  stretch={false}
                  contentStyle={styles.balanceCardContent}
                >
                  <Text style={styles.balanceLabel}>{entry.leave_type_name}</Text>
                  <Text style={styles.balanceValue}>
                    {t("leave.history.daysLeft", { count: entry.remaining_days })}
                  </Text>
                </ClaySurface>
              ))}
            </View>
          </>
        }
        ListEmptyComponent={
          <View style={styles.centered}>
            <Text style={styles.meta}>{error || t("leave.history.noResults")}</Text>
          </View>
        }
        renderItem={({ item }) => (
          <View style={styles.row}>
            <View>
              <Text style={styles.type}>{item.leave_type_name}</Text>
              <Text style={styles.meta}>
                {formatDate(item.start_date)} – {formatDate(item.end_date)} (
                {t("leave.history.dayCount", { count: item.days_requested })})
              </Text>
            </View>
            <View
              style={[
                styles.statusPill,
                { backgroundColor: `${statusColors[item.status] ?? colors.textMuted}1a` },
              ]}
            >
              <Text style={[styles.status, { color: statusColors[item.status] ?? colors.textMuted }]}>
                {t(`leaveStatus.${item.status}`, { defaultValue: item.status })}
              </Text>
            </View>
          </View>
        )}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: colors.background },
  container: { flex: 1, backgroundColor: colors.background },
  headerRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 24,
    paddingTop: 24,
    marginBottom: 16,
  },
  title: { fontSize: 24, fontWeight: "600" },
  centered: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
    backgroundColor: colors.background,
  },
  balanceRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: "#f3f4f6",
  },
  balanceCardContent: { paddingHorizontal: 12, paddingVertical: 8 },
  balanceLabel: { fontSize: 12, color: "#6b7280" },
  balanceValue: { fontSize: 14, fontWeight: "600", color: "#111827" },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: "#f3f4f6",
  },
  type: { fontSize: 16, fontWeight: "600", color: "#111827" },
  meta: { marginTop: 2, color: "#6b7280" },
  statusPill: { borderRadius: 999, paddingHorizontal: 10, paddingVertical: 4 },
  status: { fontWeight: "600", color: "#374151" },
});
