import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from "react-native";
import { getHistory } from "@/services/api/endpoints/attendance";

const STATUS_LABELS = {
  PRESENT: "Present",
  LATE: "Late",
  EARLY_DEPARTURE: "Early Departure",
  OVERTIME: "Overtime",
  ABSENT: "Absent",
};

function formatDate(isoDate) {
  return new Date(isoDate).toLocaleDateString([], {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

export default function HistoryScreen() {
  const [records, setRecords] = useState([]);
  const [nextUrl, setNextUrl] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState(null);

  const loadFirstPage = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getHistory();
      setRecords(data.results);
      setNextUrl(data.next);
    } catch (err) {
      setError(err.message || "Unable to load attendance history.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadFirstPage();
  }, [loadFirstPage]);

  async function loadNextPage() {
    if (!nextUrl || isLoadingMore) return;
    setIsLoadingMore(true);
    try {
      const data = await getHistory(nextUrl);
      setRecords((prev) => [...prev, ...data.results]);
      setNextUrl(data.next);
    } catch {
      // A failed "load more" leaves the existing list intact — no need to
      // surface a blocking error for a background pagination fetch.
    } finally {
      setIsLoadingMore(false);
    }
  }

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.centered}>
        <Text style={styles.error}>{error}</Text>
      </View>
    );
  }

  return (
    <FlatList
      style={styles.container}
      data={records}
      keyExtractor={(item) => item.id}
      onEndReached={loadNextPage}
      onEndReachedThreshold={0.4}
      ListEmptyComponent={
        <View style={styles.centered}>
          <Text style={styles.meta}>No attendance history yet.</Text>
        </View>
      }
      ListFooterComponent={isLoadingMore ? <ActivityIndicator style={styles.footer} /> : null}
      renderItem={({ item }) => (
        <View style={styles.row}>
          <View>
            <Text style={styles.date}>{formatDate(item.attendance_date)}</Text>
            {item.branch && <Text style={styles.meta}>{item.branch.name}</Text>}
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
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: "#f3f4f6",
  },
  date: { fontSize: 16, fontWeight: "600", color: "#111827" },
  meta: { marginTop: 2, color: "#6b7280" },
  status: { fontWeight: "600", color: "#374151" },
  error: { color: "#dc2626" },
  footer: { marginVertical: 16 },
});
