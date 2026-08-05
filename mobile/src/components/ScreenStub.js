import { View, Text, StyleSheet } from "react-native";
import { useI18n } from "@/i18n";
import { colors } from "@/theme/colors";

// Placeholder for screens built in later phases (see docs/05-DEVELOPMENT-ROADMAP.md).
export default function ScreenStub({ title }) {
  const { t } = useI18n();
  return (
    <View style={styles.container}>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.subtitle}>{t("screenStub.comingSoon")}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, backgroundColor: colors.background },
  title: { fontSize: 20, fontWeight: "600" },
  subtitle: { marginTop: 8, color: "#6b7280" },
});
