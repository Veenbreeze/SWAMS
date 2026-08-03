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
import { getLeaveTypes, submitLeaveRequest } from "@/services/api/endpoints/leave";

export default function LeaveRequestScreen({ navigation }) {
  // `undefined` = still loading the leave-type list.
  const [leaveTypes, setLeaveTypes] = useState(undefined);
  const [leaveTypeId, setLeaveTypeId] = useState(null);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
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

  async function handleSubmit() {
    setError(null);
    if (!leaveTypeId || !startDate || !endDate) {
      setError("Please choose a leave type and both dates.");
      return;
    }
    setIsSubmitting(true);
    try {
      await submitLeaveRequest({ leaveTypeId, startDate, endDate, reason });
      setStartDate("");
      setEndDate("");
      setReason("");
      navigation.navigate("LeaveHistory");
    } catch (err) {
      setError(err.message || "Unable to submit leave request.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (leaveTypes === undefined) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.label}>Leave type</Text>
      <View style={styles.typeRow}>
        {leaveTypes.map((type) => (
          <Pressable
            key={type.id}
            style={[styles.typeChip, leaveTypeId === type.id && styles.typeChipSelected]}
            onPress={() => setLeaveTypeId(type.id)}
          >
            <Text
              style={[
                styles.typeChipText,
                leaveTypeId === type.id && styles.typeChipTextSelected,
              ]}
            >
              {type.name}
            </Text>
          </Pressable>
        ))}
      </View>
      {leaveTypes.length === 0 && <Text style={styles.meta}>No leave types configured yet.</Text>}

      <Text style={styles.label}>Start date</Text>
      <TextInput
        style={styles.input}
        placeholder="YYYY-MM-DD"
        value={startDate}
        onChangeText={setStartDate}
        autoCapitalize="none"
      />

      <Text style={styles.label}>End date</Text>
      <TextInput
        style={styles.input}
        placeholder="YYYY-MM-DD"
        value={endDate}
        onChangeText={setEndDate}
        autoCapitalize="none"
      />

      <Text style={styles.label}>Reason</Text>
      <TextInput
        style={[styles.input, styles.multiline]}
        multiline
        value={reason}
        onChangeText={setReason}
      />

      {error && <Text style={styles.error}>{error}</Text>}

      <Pressable style={styles.button} onPress={handleSubmit} disabled={isSubmitting}>
        {isSubmitting ? (
          <ActivityIndicator color="#ffffff" />
        ) : (
          <Text style={styles.buttonText}>Submit request</Text>
        )}
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#ffffff" },
  content: { padding: 24 },
  centered: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#ffffff" },
  label: { fontSize: 13, color: "#6b7280", marginBottom: 6, marginTop: 16 },
  input: {
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  multiline: { minHeight: 80, textAlignVertical: "top" },
  typeRow: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  typeChip: {
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 8,
  },
  typeChipSelected: { backgroundColor: "#111827", borderColor: "#111827" },
  typeChipText: { color: "#111827", fontWeight: "500" },
  typeChipTextSelected: { color: "#ffffff" },
  meta: { color: "#6b7280", marginTop: 8 },
  error: { color: "#dc2626", marginTop: 16 },
  button: {
    backgroundColor: "#111827",
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: "center",
    marginTop: 24,
  },
  buttonText: { color: "#ffffff", fontWeight: "600" },
});
