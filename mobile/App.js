import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { I18nProvider } from "@/i18n";
import { AuthProvider } from "@/context/AuthContext";
import RootNavigator from "@/navigation/RootNavigator";

export default function App() {
  return (
    <SafeAreaProvider>
      <I18nProvider>
        <AuthProvider>
          <RootNavigator />
          <StatusBar style="auto" />
        </AuthProvider>
      </I18nProvider>
    </SafeAreaProvider>
  );
}
