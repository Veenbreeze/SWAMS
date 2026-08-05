import { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Image,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "@/hooks/useAuth";
import { useI18n } from "@/i18n";
import { getToday } from "@/services/api/endpoints/attendance";
import { getLeaveRequests } from "@/services/api/endpoints/leave";
import {
  getNotifications,
  getUnreadCount,
  markNotificationRead,
} from "@/services/api/endpoints/notifications";
import { colors, statusColors } from "@/theme/colors";
import { clayRadius } from "@/theme/clay";
import { ClaySurface, ClayIconBadge } from "@/components/clay";

function formatTime(isoString) {
  return new Date(isoString).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatDate(isoDate) {
  return new Date(isoDate).toLocaleDateString([], { year: "numeric", month: "short", day: "numeric" });
}

export default function DashboardScreen({ navigation }) {
  const { t } = useI18n();
  const { user } = useAuth();
  const employee = user?.employee;
  const [today, setToday] = useState(undefined);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifications, setNotifications] = useState([]);
  const [recentLeave, setRecentLeave] = useState([]);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const load = useCallback(async () => {
    const [todayResult, unread, notificationsResult, leaveResult] = await Promise.all([
      getToday().catch(() => null),
      getUnreadCount().catch(() => 0),
      getNotifications({ page_size: 2 }).catch(() => null),
      getLeaveRequests({ page_size: 2 }).catch(() => null),
    ]);
    setToday(todayResult);
    setUnreadCount(unread);
    setNotifications(notificationsResult?.results ?? []);
    setRecentLeave(leaveResult?.results ?? []);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleRefresh() {
    setIsRefreshing(true);
    await load();
    setIsRefreshing(false);
  }

  async function handleMarkRead(notification) {
    if (notification.is_read) return;
    setNotifications((prev) =>
      prev.map((item) => (item.id === notification.id ? { ...item, is_read: true } : item))
    );
    setUnreadCount((prev) => Math.max(0, prev - 1));
    try {
      await markNotificationRead(notification.id);
    } catch {
      // Best-effort — a failed mark-as-read just leaves it unread next load.
    }
  }

  if (today === undefined) {
    return (
      <SafeAreaView style={styles.centered} edges={["top"]}>
        <ActivityIndicator />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safeArea} edges={["top"]}>
      <ScrollView
        style={styles.container}
        refreshControl={<RefreshControl refreshing={isRefreshing} onRefresh={handleRefresh} />}
      >
        <Text style={styles.greeting}>
          {employee
            ? t("dashboard.greetingWithName", { name: employee.first_name })
            : t("dashboard.greetingDefault")}
        </Text>

        {employee && (
          <ClaySurface radius={clayRadius.lg} contentStyle={styles.cardContent} style={styles.cardWrapper}>
            <View style={styles.profileRow}>
              {employee.profile_picture_url ? (
                <ClayIconBadge size={56} backgroundColor={colors.surfaceMuted} subtle>
                  <Image source={{ uri: employee.profile_picture_url }} style={styles.avatarImage} />
                </ClayIconBadge>
              ) : (
                <ClayIconBadge size={56} backgroundColor={colors.surfaceMuted} subtle>
                  <Text style={styles.avatarInitial}>
                    {employee.first_name?.[0]?.toUpperCase() ?? "?"}
                  </Text>
                </ClayIconBadge>
              )}
              <View style={styles.profileInfo}>
                <Text style={styles.profileName}>
                  {employee.first_name} {employee.last_name}
                </Text>
                <Text style={styles.meta}>{employee.employee_number}</Text>
                {employee.position ? <Text style={styles.meta}>{employee.position}</Text> : null}
              </View>
            </View>

            <View style={styles.divider} />

            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>{t("profile.email")}</Text>
              <Text style={styles.detailValue}>{user.email}</Text>
            </View>
            {employee.phone ? (
              <View style={styles.detailRow}>
                <Text style={styles.detailLabel}>{t("profile.phone")}</Text>
                <Text style={styles.detailValue}>{employee.phone}</Text>
              </View>
            ) : null}
            {today?.branch?.name ? (
              <View style={styles.detailRow}>
                <Text style={styles.detailLabel}>{t("dashboard.branch")}</Text>
                <Text style={styles.detailValue}>{today.branch.name}</Text>
              </View>
            ) : null}
            {employee.joining_date ? (
              <View style={styles.detailRow}>
                <Text style={styles.detailLabel}>{t("dashboard.joined")}</Text>
                <Text style={styles.detailValue}>{formatDate(employee.joining_date)}</Text>
              </View>
            ) : null}
            {employee.employment_status ? (
              <View style={styles.detailRow}>
                <Text style={styles.detailLabel}>{t("dashboard.status")}</Text>
                <View
                  style={[
                    styles.statusPill,
                    {
                      backgroundColor: `${statusColors.APPROVED ?? colors.secondary}1a`,
                    },
                  ]}
                >
                  <Text style={[styles.statusPillText, { color: statusColors.APPROVED }]}>
                    {employee.employment_status}
                  </Text>
                </View>
              </View>
            ) : null}
          </ClaySurface>
        )}

        <ClaySurface radius={clayRadius.lg} contentStyle={styles.cardContent} style={styles.cardWrapper}>
          <Text style={styles.cardLabel}>{t("dashboard.today")}</Text>
          {today ? (
            <>
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
              {today.check_in_time && (
                <Text style={styles.meta}>
                  {t("dashboard.checkedIn", { time: formatTime(today.check_in_time) })}
                </Text>
              )}
              {today.check_out_time && (
                <Text style={styles.meta}>
                  {t("dashboard.checkedOut", { time: formatTime(today.check_out_time) })}
                </Text>
              )}
            </>
          ) : (
            <Text style={styles.meta}>{t("dashboard.notCheckedInYet")}</Text>
          )}
        </ClaySurface>

        <ClaySurface radius={clayRadius.lg} contentStyle={styles.cardContent} style={styles.cardWrapper}>
          <Text style={styles.cardLabel}>{t("dashboard.recentLeave")}</Text>
          {recentLeave.length === 0 ? (
            <Text style={styles.meta}>{t("dashboard.noLeaveRequests")}</Text>
          ) : (
            recentLeave.map((item) => (
              <View key={item.id} style={styles.leaveRow}>
                <View style={styles.leaveRowInfo}>
                  <Text style={styles.leaveType}>{item.leave_type_name}</Text>
                  <Text style={styles.meta}>
                    {formatDate(item.start_date)} – {formatDate(item.end_date)}
                  </Text>
                </View>
                <View
                  style={[
                    styles.statusPill,
                    { backgroundColor: `${statusColors[item.status] ?? colors.textMuted}1a` },
                  ]}
                >
                  <Text
                    style={[
                      styles.statusPillText,
                      { color: statusColors[item.status] ?? colors.textMuted },
                    ]}
                  >
                    {t(`leaveStatus.${item.status}`, { defaultValue: item.status })}
                  </Text>
                </View>
              </View>
            ))
          )}
          <Pressable
            style={styles.seeMoreButton}
            onPress={() => navigation.navigate("Leave", { screen: "LeaveHistory" })}
          >
            <Text style={styles.seeMoreText}>{t("dashboard.seeMore")}</Text>
            <Ionicons name="chevron-forward" size={16} color={colors.primary} />
          </Pressable>
        </ClaySurface>

        <ClaySurface radius={clayRadius.lg} contentStyle={styles.cardContent} style={styles.cardWrapper}>
          <View style={styles.cardHeaderRow}>
            <Text style={styles.cardLabel}>{t("dashboard.notifications")}</Text>
            <Text style={styles.unreadBadge}>{t("dashboard.unread", { count: unreadCount })}</Text>
          </View>
          {notifications.length === 0 ? (
            <Text style={styles.meta}>{t("dashboard.noNotifications")}</Text>
          ) : (
            notifications.map((notification) => (
              <Pressable
                key={notification.id}
                style={styles.notificationRow}
                onPress={() => handleMarkRead(notification)}
              >
                <View
                  style={[
                    styles.statusDot,
                    styles.notificationDot,
                    notification.is_read ? styles.readDot : styles.secondaryDot,
                  ]}
                />
                <View style={styles.notificationInfo}>
                  <Text
                    style={[styles.notificationTitle, notification.is_read && styles.readText]}
                    numberOfLines={1}
                  >
                    {notification.title}
                  </Text>
                  <Text style={styles.meta} numberOfLines={2}>
                    {notification.message}
                  </Text>
                </View>
              </Pressable>
            ))
          )}
        </ClaySurface>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: colors.background },
  container: { flex: 1, backgroundColor: colors.background, padding: 24 },
  centered: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: colors.background },
  greeting: { fontSize: 24, fontWeight: "600", marginBottom: 24 },
  cardWrapper: { marginBottom: 20 },
  cardContent: { padding: 16 },
  cardLabel: { color: "#6b7280", marginBottom: 6 },
  cardHeaderRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  unreadBadge: { color: colors.secondary, fontWeight: "700", fontSize: 12 },
  profileRow: { flexDirection: "row", alignItems: "center", gap: 12 },
  avatarImage: { width: 56, height: 56 },
  avatarInitial: { fontSize: 22, fontWeight: "700", color: colors.primary },
  profileInfo: { flex: 1 },
  profileName: { fontSize: 17, fontWeight: "700", color: "#111827" },
  divider: { height: 1, backgroundColor: colors.cardBorder, marginVertical: 14 },
  detailRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 8,
  },
  detailLabel: { color: "#6b7280", fontSize: 13 },
  detailValue: { color: "#111827", fontSize: 13, fontWeight: "600" },
  statusPill: { borderRadius: 999, paddingHorizontal: 10, paddingVertical: 3 },
  statusPillText: { fontSize: 12, fontWeight: "700" },
  statusRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  statusDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: colors.primary },
  secondaryDot: { backgroundColor: colors.secondary },
  readDot: { backgroundColor: colors.cardBorder },
  status: { fontSize: 20, fontWeight: "700", color: "#111827" },
  meta: { marginTop: 8, color: "#6b7280" },
  leaveRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 10,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: colors.cardBorder,
  },
  leaveRowInfo: { flex: 1, marginRight: 8 },
  leaveType: { fontSize: 14, fontWeight: "600", color: "#111827" },
  seeMoreButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 4,
    marginTop: 14,
    paddingTop: 14,
    borderTopWidth: 1,
    borderTopColor: colors.cardBorder,
  },
  seeMoreText: { color: colors.primary, fontWeight: "600", fontSize: 13 },
  notificationRow: {
    flexDirection: "row",
    marginTop: 10,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: colors.cardBorder,
  },
  notificationDot: { marginTop: 5, marginRight: 10 },
  notificationInfo: { flex: 1 },
  notificationTitle: { fontSize: 14, fontWeight: "600", color: "#111827" },
  readText: { color: "#6b7280", fontWeight: "500" },
});
