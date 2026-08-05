import { View, Text, ActivityIndicator, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useI18n } from "@/i18n";
import { colors } from "@/theme/colors";
import { ClayIconBadge } from "@/components/clay";

export default function SplashScreen() {
  const { t } = useI18n();
  return (
    <View style={styles.container}>
      <ClayIconBadge size={84} backgroundColor={colors.primary} style={styles.badge}>
        <Ionicons name="business" size={38} color={colors.primaryForeground} />
      </ClayIconBadge>
      <Text style={styles.title}>{t("splash.appName")}</Text>
      <ActivityIndicator style={styles.spinner} color={colors.primary} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.background,
  },
  badge: { marginBottom: 20 },
  title: {
    fontSize: 28,
    fontWeight: "600",
    marginBottom: 16,
    color: colors.primary,
  },
  spinner: {
    marginTop: 12,
  },
});
