import { View, Text, StyleSheet } from "react-native";

export default function ForceChangePasswordScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Change your password to continue</Text>
      <Text style={styles.subtitle}>
        This screen will be implemented in a later development phase.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", padding: 24, backgroundColor: "#ffffff" },
  title: { fontSize: 20, fontWeight: "600" },
  subtitle: { marginTop: 8, color: "#6b7280" },
});
