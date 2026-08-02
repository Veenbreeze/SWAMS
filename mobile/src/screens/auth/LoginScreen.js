import { useState } from "react";
import { View, Text, TextInput, Pressable, StyleSheet, ActivityIndicator } from "react-native";
import { useAuth } from "@/hooks/useAuth";

export default function LoginScreen() {
  const { login } = useAuth();
  const [organizationCode, setOrganizationCode] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit() {
    setError(null);
    setIsSubmitting(true);
    try {
      await login({ organizationCode, identifier, password });
    } catch (err) {
      setError(err.message || "Unable to sign in. Check your credentials and try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Sign in to SWAMS</Text>

      <Text style={styles.label}>Organization code</Text>
      <TextInput
        style={styles.input}
        placeholder="ABC001"
        autoCapitalize="characters"
        value={organizationCode}
        onChangeText={setOrganizationCode}
      />

      <Text style={styles.label}>Email or employee ID</Text>
      <TextInput
        style={styles.input}
        autoCapitalize="none"
        value={identifier}
        onChangeText={setIdentifier}
      />

      <Text style={styles.label}>Password</Text>
      <TextInput
        style={styles.input}
        secureTextEntry
        value={password}
        onChangeText={setPassword}
      />

      {error && <Text style={styles.error}>{error}</Text>}

      <Pressable style={styles.button} onPress={handleSubmit} disabled={isSubmitting}>
        {isSubmitting ? (
          <ActivityIndicator color="#ffffff" />
        ) : (
          <Text style={styles.buttonText}>Sign in</Text>
        )}
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", padding: 24, backgroundColor: "#ffffff" },
  title: { fontSize: 24, fontWeight: "600", marginBottom: 24 },
  label: { fontSize: 13, color: "#6b7280", marginBottom: 4, marginTop: 12 },
  input: {
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  error: { color: "#dc2626", marginTop: 12 },
  button: {
    backgroundColor: "#111827",
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: "center",
    marginTop: 24,
  },
  buttonText: { color: "#ffffff", fontWeight: "600" },
});
