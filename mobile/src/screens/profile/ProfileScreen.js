import { useState } from "react";
import {
  ActivityIndicator,
  Image,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useAuth } from "@/hooks/useAuth";
import { useI18n } from "@/i18n";
import {
  requestProfilePictureUpload,
  updateMyPhone,
  uploadToSignedUrl,
} from "@/services/api/endpoints/employees";
import {
  captureProfilePicture,
  pickProfilePictureFromLibrary,
} from "@/services/camera/profilePicture";
import { colors } from "@/theme/colors";
import { clayRadius } from "@/theme/clay";
import { ClaySurface, ClayButton, ClayInputRow, ClayIconBadge } from "@/components/clay";

export default function ProfileScreen() {
  const { t } = useI18n();
  const { user, updateEmployee } = useAuth();
  const employee = user?.employee;

  const [phone, setPhone] = useState(employee?.phone ?? "");
  const [pictureUrl, setPictureUrl] = useState(employee?.profile_picture_url ?? null);
  const [isSavingPhone, setIsSavingPhone] = useState(false);
  const [isUploadingPicture, setIsUploadingPicture] = useState(false);
  const [error, setError] = useState(null);
  const [savedMessage, setSavedMessage] = useState(null);

  if (!employee) {
    return (
      <SafeAreaView style={styles.centered} edges={["top"]}>
        <Text style={styles.meta}>{t("profile.noEmployeeProfile")}</Text>
      </SafeAreaView>
    );
  }

  async function handleSavePhone() {
    setError(null);
    setSavedMessage(null);
    setIsSavingPhone(true);
    try {
      await updateMyPhone({ employeeId: employee.id, phone });
      updateEmployee({ phone });
      setSavedMessage(t("profile.saved"));
    } catch (err) {
      setError(err.message || t("profile.genericError"));
    } finally {
      setIsSavingPhone(false);
    }
  }

  async function handlePickPicture(pickerFn) {
    setError(null);
    setIsUploadingPicture(true);
    try {
      const asset = await pickerFn();
      if (!asset) {
        setIsUploadingPicture(false);
        return;
      }
      const contentType = asset.mimeType || "image/jpeg";
      const { upload_url: uploadUrl, profile_picture_url: newUrl } =
        await requestProfilePictureUpload({
          employeeId: employee.id,
          contentType,
          fileSize: asset.fileSize ?? 0,
        });
      await uploadToSignedUrl({ uploadUrl, uri: asset.uri, contentType });
      setPictureUrl(newUrl);
      updateEmployee({ profile_picture_url: newUrl });
    } catch (err) {
      setError(err.message || t("profile.genericError"));
    } finally {
      setIsUploadingPicture(false);
    }
  }

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.avatarSection}>
          {pictureUrl ? (
            <ClayIconBadge size={96} backgroundColor={colors.surface}>
              <Image source={{ uri: pictureUrl }} style={styles.avatarImage} />
            </ClayIconBadge>
          ) : (
            <ClayIconBadge size={96} backgroundColor={colors.surface}>
              <Text style={styles.avatarInitial}>
                {employee.first_name?.[0]?.toUpperCase() ?? "?"}
              </Text>
            </ClayIconBadge>
          )}
          {isUploadingPicture ? (
            <ActivityIndicator style={styles.avatarSpinner} />
          ) : (
            <View style={styles.avatarButtons}>
              <Pressable
                style={styles.linkButton}
                onPress={() => handlePickPicture(pickProfilePictureFromLibrary)}
              >
                <Text style={styles.linkButtonText}>{t("profile.chooseFromLibrary")}</Text>
              </Pressable>
              <Pressable
                style={styles.linkButton}
                onPress={() => handlePickPicture(captureProfilePicture)}
              >
                <Text style={styles.linkButtonTextSecondary}>{t("profile.takePhoto")}</Text>
              </Pressable>
            </View>
          )}
        </View>

        <Text style={styles.name}>
          {employee.first_name} {employee.last_name}
        </Text>
        <Text style={styles.meta}>{employee.employee_number}</Text>
        {employee.position ? <Text style={styles.meta}>{employee.position}</Text> : null}

        <ClaySurface radius={clayRadius.lg} contentStyle={styles.cardContent} style={styles.cardWrapper}>
          <View style={styles.field}>
            <Text style={styles.label}>{t("profile.email")}</Text>
            <Text style={styles.value}>{user.email}</Text>
          </View>

          <View style={styles.fieldSpacing}>
            <Text style={styles.label}>{t("profile.phone")}</Text>
            <ClayInputRow>
              <TextInput
                style={styles.input}
                value={phone}
                onChangeText={setPhone}
                keyboardType="phone-pad"
              />
            </ClayInputRow>
          </View>

          {error && <Text style={styles.error}>{error}</Text>}
          {savedMessage && <Text style={styles.saved}>{savedMessage}</Text>}

          <ClayButton
            title={t("common.save")}
            onPress={handleSavePhone}
            loading={isSavingPhone}
            style={styles.button}
          />
        </ClaySurface>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content: { padding: 24, alignItems: "center" },
  centered: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: colors.background,
  },
  avatarSection: { alignItems: "center", marginBottom: 16 },
  avatarImage: { width: 96, height: 96 },
  avatarInitial: { fontSize: 32, fontWeight: "700", color: "#6b7280" },
  avatarSpinner: { marginTop: 12 },
  avatarButtons: { flexDirection: "row", gap: 16, marginTop: 12 },
  linkButton: { paddingVertical: 4 },
  linkButtonText: { color: colors.primary, fontWeight: "600", fontSize: 13 },
  linkButtonTextSecondary: { color: colors.secondary, fontWeight: "600", fontSize: 13 },
  name: { fontSize: 20, fontWeight: "700", color: "#111827", marginTop: 8 },
  meta: { color: "#6b7280", marginTop: 2 },
  cardWrapper: { width: "100%", marginTop: 20 },
  cardContent: { padding: 20 },
  field: { width: "100%" },
  fieldSpacing: { width: "100%", marginTop: 16 },
  label: { fontSize: 13, color: "#6b7280", marginBottom: 6 },
  value: { fontSize: 16, color: "#111827" },
  input: { flex: 1, color: colors.text },
  error: { color: "#dc2626", marginTop: 16, alignSelf: "flex-start" },
  saved: { color: "#059669", marginTop: 16, alignSelf: "flex-start" },
  button: { marginTop: 24 },
});
