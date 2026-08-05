import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import DateTimePicker from "@react-native-community/datetimepicker";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { getLeaveTypes, submitLeaveRequest } from "@/services/api/endpoints/leave";
import { useI18n } from "@/i18n";
import { colors } from "@/theme/colors";
import { ClayButton, ClayChip, ClayInputRow } from "@/components/clay";

function toApiDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export default function LeaveRequestScreen({ navigation }) {
  const { t } = useI18n();
  // `undefined` = still loading the leave-type list.
  const [leaveTypes, setLeaveTypes] = useState(undefined);
  const [leaveTypeId, setLeaveTypeId] = useState(null);
  const [startDate, setStartDate] = useState(null);
  const [endDate, setEndDate] = useState(null);
  const [activePicker, setActivePicker] = useState(null); // "start" | "end" | null
  const [reason, setReason] = useState("");
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    getLeaveTypes()
      .then((types) => {
        setLeaveTypes(types);
        if (types.length > 0) setLeaveTypeId(types[0].id);
      })
      .catch(() => setLeaveTypes([]));
  }, []);

  function handleDateChange(event, selectedDate) {
    const picker = activePicker;
    setActivePicker(null);
    if (event.type === "dismissed" || !selectedDate) return;
    if (picker === "start") setStartDate(selectedDate);
    else if (picker === "end") setEndDate(selectedDate);
  }

  async function handleSubmit() {
    setError(null);
    if (!leaveTypeId || !startDate || !endDate) {
      setError(t("leave.request.validationError"));
      return;
    }
    setIsSubmitting(true);
    try {
      await submitLeaveRequest({
        leaveTypeId,
        startDate: toApiDate(startDate),
        endDate: toApiDate(endDate),
        reason,
      });
      setStartDate(null);
      setEndDate(null);
      setReason("");
      navigation.navigate("LeaveHistory");
    } catch (err) {
      setError(err.message || t("leave.request.genericError"));
    } finally {
      setIsSubmitting(false);
    }
  }

  if (leaveTypes === undefined) {
    return (
      <SafeAreaView style={styles.centered} edges={["top"]}>
        <ActivityIndicator />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safeArea} edges={["top"]}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>{t("nav.requestLeave")}</Text>
        <Text style={styles.label}>{t("leave.request.leaveType")}</Text>
        <View style={styles.typeRow}>
          {leaveTypes.map((type) => (
            <ClayChip
              key={type.id}
              label={type.name}
              selected={leaveTypeId === type.id}
              onPress={() => setLeaveTypeId(type.id)}
            />
          ))}
        </View>
        {leaveTypes.length === 0 && (
          <Text style={styles.meta}>{t("leave.request.noLeaveTypes")}</Text>
        )}

        <Text style={styles.label}>{t("leave.request.startDate")}</Text>
        <Pressable onPress={() => setActivePicker("start")}>
          <ClayInputRow>
            <Ionicons
              name="calendar-outline"
              size={18}
              color={colors.textMuted}
              style={styles.inputIcon}
            />
            <Text style={[styles.dateText, !startDate && styles.datePlaceholder]}>
              {startDate
                ? startDate.toLocaleDateString([], { year: "numeric", month: "short", day: "numeric" })
                : t("leave.request.selectDate")}
            </Text>
          </ClayInputRow>
        </Pressable>

        <Text style={styles.label}>{t("leave.request.endDate")}</Text>
        <Pressable onPress={() => setActivePicker("end")}>
          <ClayInputRow>
            <Ionicons
              name="calendar-outline"
              size={18}
              color={colors.textMuted}
              style={styles.inputIcon}
            />
            <Text style={[styles.dateText, !endDate && styles.datePlaceholder]}>
              {endDate
                ? endDate.toLocaleDateString([], { year: "numeric", month: "short", day: "numeric" })
                : t("leave.request.selectDate")}
            </Text>
          </ClayInputRow>
        </Pressable>

        {activePicker && (
          <DateTimePicker
            value={(activePicker === "start" ? startDate : endDate) || new Date()}
            mode="date"
            display="default"
            minimumDate={activePicker === "end" ? startDate ?? undefined : undefined}
            onChange={handleDateChange}
          />
        )}

        <Text style={styles.label}>{t("leave.request.reason")}</Text>
        <ClayInputRow multiline>
          <TextInput
            style={[styles.input, styles.multiline]}
            multiline
            value={reason}
            onChangeText={setReason}
          />
        </ClayInputRow>

        {error && <Text style={styles.error}>{error}</Text>}

        <ClayButton
          title={t("leave.request.submit")}
          onPress={handleSubmit}
          loading={isSubmitting}
          style={styles.button}
        />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: colors.background },
  content: { padding: 24 },
  title: { fontSize: 24, fontWeight: "600", marginBottom: 24 },
  centered: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: colors.background,
  },
  label: { fontSize: 13, color: "#6b7280", marginBottom: 6, marginTop: 16 },
  input: { flex: 1, color: colors.text },
  inputIcon: { marginRight: 8 },
  dateText: { color: colors.text },
  datePlaceholder: { color: colors.textMuted },
  multiline: { minHeight: 80, textAlignVertical: "top" },
  typeRow: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  meta: { color: "#6b7280", marginTop: 8 },
  error: { color: "#dc2626", marginTop: 16 },
  button: { marginTop: 24 },
});
