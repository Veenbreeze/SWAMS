import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { getHistory } from "@/services/api/endpoints/attendance";
import { useI18n } from "@/i18n";
import { colors, statusColors } from "@/theme/colors";

function formatDate(isoDate) {
  return new Date(isoDate).toLocaleDateString([], {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

export default function HistoryScreen() {
  const { t } = useI18n();
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
      setError(err.message || t("history.genericError"));
    } finally {
      setIsLoading(false);
    }
  }, [t]);

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
      <SafeAreaView style={styles.centered} edges={["top"]}>
        <ActivityIndicator />
      </SafeAreaView>
    );
  }

  if (error) {
    return (
      <SafeAreaView style={styles.centered} edges={["top"]}>
        <Text style={styles.error}>{error}</Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safeArea} edges={["top"]}>
      <FlatList
        style={styles.container}
        data={records}
        keyExtractor={(item) => item.id}
        onEndReached={loadNextPage}
        onEndReachedThreshold={0.4}
        ListHeaderComponent={
          <Text style={styles.title}>{t("nav.history")}</Text>
        }
        ListEmptyComponent={
          <View style={styles.centered}>
            <Text style={styles.meta}>{t("history.noResults")}</Text>
          </View>
        }
        ListFooterComponent={isLoadingMore ? <ActivityIndicator style={styles.footer} /> : null}
        renderItem={({ item }) => (
          <View style={styles.row}>
            <View>
              <Text style={styles.date}>{formatDate(item.attendance_date)}</Text>
              {item.branch && <Text style={styles.meta}>{item.branch.name}</Text>}
            </View>
            <View
              style={[
                styles.statusPill,
                { backgroundColor: `${statusColors[item.status] ?? colors.textMuted}1a` },
              ]}
            >
              <Text style={[styles.status, { color: statusColors[item.status] ?? colors.textMuted }]}>
                {t(`attendanceStatus.${item.status}`, { defaultValue: item.status })}
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
  title: {
    fontSize: 24,
    fontWeight: "600",
    marginBottom: 24,
    paddingHorizontal: 24,
    paddingTop: 24,
  },
  centered: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
    backgroundColor: colors.background,
  },
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
  meta: { marginTop: 8, color: "#6b7280" },
  statusPill: { borderRadius: 999, paddingHorizontal: 10, paddingVertical: 4 },
  status: { fontWeight: "600", color: "#374151" },
  error: { color: "#dc2626" },
  footer: { marginVertical: 16 },
});
