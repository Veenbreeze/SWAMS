import { View, Text, StyleSheet } from "react-native";

// Placeholder for screens built in later phases (see docs/05-DEVELOPMENT-ROADMAP.md).
export default function ScreenStub({ title }) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.subtitle}>
        This screen will be implemented in a later development phase.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, backgroundColor: "#ffffff" },
  title: { fontSize: 20, fontWeight: "600" },
  subtitle: { marginTop: 8, color: "#6b7280" },
});
