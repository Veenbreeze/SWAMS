import { View, Text, ActivityIndicator, StyleSheet } from "react-native";

export default function SplashScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>SWAMS</Text>
      <ActivityIndicator style={styles.spinner} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#ffffff",
  },
  title: {
    fontSize: 28,
    fontWeight: "600",
    marginBottom: 16,
  },
  spinner: {
    marginTop: 8,
  },
});
