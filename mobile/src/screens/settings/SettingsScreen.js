import { View, Text, Pressable, StyleSheet } from "react-native";
import { useAuth } from "@/hooks/useAuth";

export default function SettingsScreen() {
  const { user, logout } = useAuth();

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Settings</Text>
      <Text style={styles.subtitle}>{user?.email}</Text>
      <Pressable style={styles.button} onPress={logout}>
        <Text style={styles.buttonText}>Log out</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, backgroundColor: "#ffffff" },
  title: { fontSize: 20, fontWeight: "600" },
  subtitle: { marginTop: 8, color: "#6b7280" },
  button: {
    marginTop: 24,
    backgroundColor: "#dc2626",
    borderRadius: 8,
    paddingVertical: 12,
    alignItems: "center",
  },
  buttonText: { color: "#ffffff", fontWeight: "600" },
});
