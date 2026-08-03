import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";
import { useAuth } from "@/hooks/useAuth";
import { getToday } from "@/services/api/endpoints/attendance";
import { getUnreadCount } from "@/services/api/endpoints/notifications";

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

export default function DashboardScreen() {
  const { user } = useAuth();
  const [today, setToday] = useState(undefined);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const load = useCallback(async () => {
    const [todayResult, unread] = await Promise.all([
      getToday().catch(() => null),
      getUnreadCount().catch(() => 0),
    ]);
    setToday(todayResult);
    setUnreadCount(unread);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleRefresh() {
    setIsRefreshing(true);
    await load();
    setIsRefreshing(false);
  }

  if (today === undefined) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator />
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={isRefreshing} onRefresh={handleRefresh} />}
    >
      <Text style={styles.greeting}>
        {user?.employee ? `Hi, ${user.employee.first_name}` : "Dashboard"}
      </Text>

      <View style={styles.card}>
        <Text style={styles.cardLabel}>Today</Text>
        {today ? (
          <>
            <Text style={styles.status}>{STATUS_LABELS[today.status] || today.status}</Text>
            {today.check_in_time && (
              <Text style={styles.meta}>Checked in {formatTime(today.check_in_time)}</Text>
            )}
            {today.check_out_time && (
              <Text style={styles.meta}>Checked out {formatTime(today.check_out_time)}</Text>
            )}
          </>
        ) : (
          <Text style={styles.meta}>You haven&rsquo;t checked in yet today.</Text>
        )}
      </View>

      <View style={styles.card}>
        <Text style={styles.cardLabel}>Notifications</Text>
        <Text style={styles.status}>{unreadCount} unread</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#ffffff", padding: 24 },
  centered: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#ffffff" },
  greeting: { fontSize: 24, fontWeight: "600", marginBottom: 24 },
  card: {
    backgroundColor: "#f9fafb",
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  cardLabel: { color: "#6b7280", marginBottom: 4 },
  status: { fontSize: 20, fontWeight: "700", color: "#111827" },
  meta: { marginTop: 4, color: "#6b7280" },
});
