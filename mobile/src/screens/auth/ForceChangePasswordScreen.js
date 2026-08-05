import { useState } from "react";
import { ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "@/hooks/useAuth";
import { useI18n } from "@/i18n";
import { colors } from "@/theme/colors";
import { clayRadius } from "@/theme/clay";
import { ClaySurface, ClayButton, ClayInputRow, ClayIconBadge } from "@/components/clay";

export default function ForceChangePasswordScreen() {
  const { t } = useI18n();
  const { completeForcedPasswordChange } = useAuth();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit() {
    setError(null);
    if (!currentPassword || !newPassword) {
      setError(t("forceChangePassword.validationError"));
      return;
    }
    if (newPassword !== confirmPassword) {
      setError(t("forceChangePassword.mismatchError"));
      return;
    }
    setIsSubmitting(true);
    try {
      await completeForcedPasswordChange({ currentPassword, newPassword });
    } catch (err) {
      setError(err.message || t("forceChangePassword.genericError"));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <SafeAreaView style={styles.safeArea} edges={["top", "bottom"]}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <ClayIconBadge size={64} backgroundColor={colors.secondary} style={styles.badge}>
          <Ionicons name="key" size={28} color="#ffffff" />
        </ClayIconBadge>
        <Text style={styles.title}>{t("forceChangePassword.title")}</Text>
        <Text style={styles.subtitle}>{t("forceChangePassword.subtitle")}</Text>

        <ClaySurface radius={clayRadius.lg} contentStyle={styles.cardContent}>
          <Text style={styles.label}>{t("forceChangePassword.currentPassword")}</Text>
          <ClayInputRow>
            <Ionicons name="lock-closed-outline" size={18} color={colors.textMuted} style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              secureTextEntry
              value={currentPassword}
              onChangeText={setCurrentPassword}
            />
          </ClayInputRow>

          <Text style={styles.label}>{t("forceChangePassword.newPassword")}</Text>
          <ClayInputRow>
            <Ionicons name="key-outline" size={18} color={colors.textMuted} style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              secureTextEntry
              value={newPassword}
              onChangeText={setNewPassword}
            />
          </ClayInputRow>

          <Text style={styles.label}>{t("forceChangePassword.confirmPassword")}</Text>
          <ClayInputRow>
            <Ionicons name="key-outline" size={18} color={colors.textMuted} style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              secureTextEntry
              value={confirmPassword}
              onChangeText={setConfirmPassword}
            />
          </ClayInputRow>

          {error && (
            <View style={styles.errorRow}>
              <Ionicons name="alert-circle-outline" size={16} color={colors.danger} />
              <Text style={styles.error}>{error}</Text>
            </View>
          )}

          <ClayButton
            title={t("forceChangePassword.submit")}
            onPress={handleSubmit}
            loading={isSubmitting}
            style={styles.button}
          />
        </ClaySurface>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: colors.background },
  content: { flexGrow: 1, justifyContent: "center", padding: 24 },
  badge: { alignSelf: "center", marginBottom: 14 },
  title: { fontSize: 20, fontWeight: "600", textAlign: "center" },
  subtitle: { marginTop: 8, color: "#6b7280", textAlign: "center", marginBottom: 24 },
  cardContent: { padding: 20 },
  label: { fontSize: 13, color: "#6b7280", marginBottom: 6, marginTop: 16 },
  inputIcon: { marginRight: 8 },
  input: { flex: 1, paddingVertical: 12, color: colors.text },
  errorRow: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: 16 },
  error: { color: colors.danger, flexShrink: 1 },
  button: { marginTop: 24 },
});
