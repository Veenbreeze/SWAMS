import { useState } from "react";
import { View, Text, Pressable, ScrollView, StyleSheet, TextInput } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "@/hooks/useAuth";
import { useI18n } from "@/i18n";
import { submitRecommendation } from "@/services/api/endpoints/recommendations";
import { colors } from "@/theme/colors";
import { clayRadius } from "@/theme/clay";
import { ClaySurface, ClayButton, ClayChip, ClayInputRow } from "@/components/clay";

const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "sw", label: "Kiswahili" },
];

export default function SettingsScreen() {
  const { user, logout, changePassword } = useAuth();
  const { t, locale, setLocale } = useI18n();

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [passwordError, setPasswordError] = useState(null);
  const [passwordSaved, setPasswordSaved] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);

  const [recommendationText, setRecommendationText] = useState("");
  const [recommendationError, setRecommendationError] = useState(null);
  const [recommendationSaved, setRecommendationSaved] = useState(false);
  const [isSubmittingRecommendation, setIsSubmittingRecommendation] = useState(false);

  async function handleChangePassword() {
    setPasswordError(null);
    setPasswordSaved(false);
    if (!currentPassword || !newPassword) {
      setPasswordError(t("settings.passwordValidationError"));
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError(t("settings.passwordMismatchError"));
      return;
    }
    setIsChangingPassword(true);
    try {
      await changePassword({ currentPassword, newPassword });
      setPasswordSaved(true);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setPasswordError(err.message || t("settings.passwordGenericError"));
    } finally {
      setIsChangingPassword(false);
    }
  }

  async function handleSubmitRecommendation() {
    setRecommendationError(null);
    setRecommendationSaved(false);
    if (!recommendationText.trim()) {
      setRecommendationError(t("settings.recommendationValidationError"));
      return;
    }
    setIsSubmittingRecommendation(true);
    try {
      await submitRecommendation(recommendationText.trim());
      setRecommendationSaved(true);
      setRecommendationText("");
    } catch (err) {
      setRecommendationError(err.message || t("settings.recommendationGenericError"));
    } finally {
      setIsSubmittingRecommendation(false);
    }
  }

  return (
    <SafeAreaView style={styles.safeArea} edges={["top"]}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>{t("settings.title")}</Text>
        <Text style={styles.subtitle}>{user?.email}</Text>

        <Text style={styles.sectionLabel}>{t("settings.language")}</Text>
        <View style={styles.languageRow}>
          {LANGUAGES.map((language) => (
            <ClayChip
              key={language.code}
              label={language.label}
              selected={locale === language.code}
              onPress={() => setLocale(language.code)}
            />
          ))}
        </View>

        <Text style={styles.sectionLabel}>{t("settings.changePassword")}</Text>
        <ClaySurface radius={clayRadius.lg} contentStyle={styles.cardContent} style={styles.cardWrapper}>
          <PasswordField
            icon="lock-closed-outline"
            placeholder={t("settings.currentPassword")}
            value={currentPassword}
            onChangeText={setCurrentPassword}
            visible={showCurrent}
            onToggleVisible={() => setShowCurrent((prev) => !prev)}
          />
          <PasswordField
            icon="key-outline"
            placeholder={t("settings.newPassword")}
            value={newPassword}
            onChangeText={setNewPassword}
            visible={showNew}
            onToggleVisible={() => setShowNew((prev) => !prev)}
            style={styles.fieldSpacing}
          />
          <PasswordField
            icon="key-outline"
            placeholder={t("settings.confirmPassword")}
            value={confirmPassword}
            onChangeText={setConfirmPassword}
            visible={showConfirm}
            onToggleVisible={() => setShowConfirm((prev) => !prev)}
            style={styles.fieldSpacing}
          />

          {passwordError && (
            <View style={styles.errorRow}>
              <Ionicons name="alert-circle-outline" size={16} color={colors.danger} />
              <Text style={styles.error}>{passwordError}</Text>
            </View>
          )}
          {passwordSaved && <Text style={styles.saved}>{t("settings.passwordSaved")}</Text>}

          <ClayButton
            title={t("settings.changePasswordSubmit")}
            variant="secondary"
            onPress={handleChangePassword}
            loading={isChangingPassword}
            style={styles.changePasswordButton}
          />
        </ClaySurface>

        <Text style={styles.sectionLabel}>{t("settings.recommendation")}</Text>
        <ClaySurface radius={clayRadius.lg} contentStyle={styles.cardContent} style={styles.cardWrapper}>
          <ClayInputRow multiline>
            <TextInput
              style={styles.textArea}
              placeholder={t("settings.recommendationPlaceholder")}
              placeholderTextColor={colors.textMuted}
              value={recommendationText}
              onChangeText={setRecommendationText}
              multiline
              numberOfLines={4}
            />
          </ClayInputRow>

          {recommendationError && (
            <View style={styles.errorRow}>
              <Ionicons name="alert-circle-outline" size={16} color={colors.danger} />
              <Text style={styles.error}>{recommendationError}</Text>
            </View>
          )}
          {recommendationSaved && <Text style={styles.saved}>{t("settings.recommendationSaved")}</Text>}

          <ClayButton
            title={t("settings.recommendationSubmit")}
            variant="secondary"
            onPress={handleSubmitRecommendation}
            loading={isSubmittingRecommendation}
            style={styles.changePasswordButton}
          />
        </ClaySurface>

        <ClayButton
          title={t("settings.logOut")}
          variant="danger"
          onPress={logout}
          style={styles.button}
        />
      </ScrollView>
    </SafeAreaView>
  );
}

function PasswordField({ icon, placeholder, value, onChangeText, visible, onToggleVisible, style }) {
  return (
    <ClayInputRow style={style}>
      <Ionicons name={icon} size={18} color={colors.textMuted} style={styles.inputIcon} />
      <TextInput
        style={styles.input}
        placeholder={placeholder}
        placeholderTextColor={colors.textMuted}
        secureTextEntry={!visible}
        value={value}
        onChangeText={onChangeText}
      />
      <Pressable onPress={onToggleVisible} hitSlop={8}>
        <Ionicons
          name={visible ? "eye-off-outline" : "eye-outline"}
          size={18}
          color={colors.textMuted}
        />
      </Pressable>
    </ClayInputRow>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: colors.background },
  content: { padding: 24 },
  title: { fontSize: 24, fontWeight: "600", marginBottom: 8 },
  subtitle: { marginTop: 0, color: "#6b7280", marginBottom: 16 },
  sectionLabel: { marginTop: 24, fontSize: 13, color: "#6b7280" },
  languageRow: { flexDirection: "row", gap: 8, marginTop: 8 },
  cardWrapper: { marginTop: 8 },
  cardContent: { padding: 16 },
  fieldSpacing: { marginTop: 12 },
  inputIcon: { marginRight: 8 },
  input: { flex: 1, paddingVertical: 10, color: colors.text },
  textArea: { flex: 1, minHeight: 72, color: colors.text, textAlignVertical: "top" },
  errorRow: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: 12 },
  error: { color: colors.danger, flexShrink: 1 },
  saved: { color: colors.success, marginTop: 12 },
  changePasswordButton: { marginTop: 16 },
  button: { marginTop: 24 },
});
