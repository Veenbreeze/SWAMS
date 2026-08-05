import { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { useAuth } from "@/hooks/useAuth";
import { useI18n } from "@/i18n";
import { colors } from "@/theme/colors";
import { clayRadius } from "@/theme/clay";
import { ClaySurface, ClayButton, ClayInputRow, ClayIconBadge } from "@/components/clay";

export default function LoginScreen() {
  const { t } = useI18n();
  const { login } = useAuth();
  const [organizationCode, setOrganizationCode] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [isPasswordVisible, setIsPasswordVisible] = useState(false);
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit() {
    setError(null);
    setIsSubmitting(true);
    try {
      await login({ organizationCode, identifier, password });
    } catch (err) {
      setError(err.message || t("login.genericError"));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <SafeAreaView style={styles.safeArea} edges={["top", "bottom"]}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
      >
        <ScrollView
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <ClayIconBadge size={76} backgroundColor={colors.primary} style={styles.logoBadge}>
            <Ionicons name="business" size={36} color={colors.primaryForeground} />
          </ClayIconBadge>
          <Text style={styles.appName}>{t("splash.appName")}</Text>
          <Text style={styles.title}>{t("login.title")}</Text>

          <ClaySurface radius={clayRadius.lg} contentStyle={styles.cardContent}>
            <Text style={styles.label}>{t("login.organizationCode")}</Text>
            <ClayInputRow>
              <Ionicons
                name="business-outline"
                size={18}
                color={colors.textMuted}
                style={styles.inputIcon}
              />
              <TextInput
                style={styles.input}
                placeholder="ABC001"
                placeholderTextColor={colors.textMuted}
                autoCapitalize="characters"
                value={organizationCode}
                onChangeText={setOrganizationCode}
              />
            </ClayInputRow>

            <Text style={styles.label}>{t("login.identifier")}</Text>
            <ClayInputRow>
              <Ionicons
                name="mail-outline"
                size={18}
                color={colors.textMuted}
                style={styles.inputIcon}
              />
              <TextInput
                style={styles.input}
                placeholder={t("login.identifierPlaceholder")}
                placeholderTextColor={colors.textMuted}
                autoCapitalize="none"
                value={identifier}
                onChangeText={setIdentifier}
              />
            </ClayInputRow>

            <Text style={styles.label}>{t("login.password")}</Text>
            <ClayInputRow>
              <Ionicons
                name="lock-closed-outline"
                size={18}
                color={colors.textMuted}
                style={styles.inputIcon}
              />
              <TextInput
                style={styles.input}
                placeholder={t("login.passwordPlaceholder")}
                placeholderTextColor={colors.textMuted}
                secureTextEntry={!isPasswordVisible}
                value={password}
                onChangeText={setPassword}
              />
              <Pressable
                onPress={() => setIsPasswordVisible((prev) => !prev)}
                hitSlop={8}
                accessibilityLabel={
                  isPasswordVisible ? t("login.hidePassword") : t("login.showPassword")
                }
              >
                <Ionicons
                  name={isPasswordVisible ? "eye-off-outline" : "eye-outline"}
                  size={18}
                  color={colors.textMuted}
                />
              </Pressable>
            </ClayInputRow>

            {error && (
              <View style={styles.errorRow}>
                <Ionicons name="alert-circle-outline" size={16} color={colors.danger} />
                <Text style={styles.error}>{error}</Text>
              </View>
            )}

            <ClayButton
              title={t("login.submit")}
              onPress={handleSubmit}
              loading={isSubmitting}
              style={styles.button}
              icon={<Ionicons name="log-in-outline" size={18} color="#ffffff" />}
            />
          </ClaySurface>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: colors.background },
  flex: { flex: 1 },
  content: { flexGrow: 1, justifyContent: "center", padding: 24 },
  logoBadge: { alignSelf: "center", marginBottom: 14 },
  appName: {
    textAlign: "center",
    fontSize: 22,
    fontWeight: "700",
    color: colors.primary,
    letterSpacing: 1,
  },
  title: {
    textAlign: "center",
    fontSize: 14,
    color: colors.textMuted,
    marginTop: 4,
    marginBottom: 28,
  },
  cardContent: { padding: 20 },
  label: { fontSize: 13, color: "#6b7280", marginBottom: 6, marginTop: 16 },
  inputIcon: { marginRight: 8 },
  input: { flex: 1, paddingVertical: 12, color: colors.text },
  errorRow: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: 16 },
  error: { color: colors.danger, flexShrink: 1 },
  button: { marginTop: 24 },
});
