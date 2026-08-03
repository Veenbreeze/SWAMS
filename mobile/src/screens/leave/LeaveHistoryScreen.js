import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from "react-native";
import { getLeaveBalance, getLeaveRequests } from "@/services/api/endpoints/leave";

const STATUS_LABELS = {
  PENDING: "Pending",
  APPROVED: "Approved",
  REJECTED: "Rejected",
  CANCELLED: "Cancelled",
};

function formatDate(isoDate) {
  return new Date(isoDate).toLocaleDateString([], { month: "short", day: "numeric" });
}

export default function LeaveHistoryScreen() {
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
      setError(err.message || "Unable to load leave history.");
      setRequests([]);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (requests === undefined) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator />
      </View>
    );
  }

  return (
    <FlatList
      style={styles.container}
      data={requests}
      keyExtractor={(item) => item.id}
      ListHeaderComponent={
        <View style={styles.balanceRow}>
          {balance.map((entry) => (
            <View key={entry.id} style={styles.balanceCard}>
              <Text style={styles.balanceLabel}>{entry.leave_type_name}</Text>
              <Text style={styles.balanceValue}>{entry.remaining_days} left</Text>
            </View>
          ))}
        </View>
      }
      ListEmptyComponent={
        <View style={styles.centered}>
          <Text style={styles.meta}>{error || "No leave requests yet."}</Text>
        </View>
      }
      renderItem={({ item }) => (
        <View style={styles.row}>
          <View>
            <Text style={styles.type}>{item.leave_type_name}</Text>
            <Text style={styles.meta}>
              {formatDate(item.start_date)} – {formatDate(item.end_date)} (
              {item.days_requested} day{item.days_requested === 1 ? "" : "s"})
            </Text>
          </View>
          <Text style={styles.status}>{STATUS_LABELS[item.status] || item.status}</Text>
        </View>
      )}
    />
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#ffffff" },
  centered: { flex: 1, justifyContent: "center", alignItems: "center", padding: 24 },
  balanceRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: "#f3f4f6",
  },
  balanceCard: {
    backgroundColor: "#f9fafb",
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
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
  status: { fontWeight: "600", color: "#374151" },
});
