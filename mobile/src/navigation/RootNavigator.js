import { NavigationContainer } from "@react-navigation/native";
import { useAuth } from "@/hooks/useAuth";
import SplashScreen from "@/screens/SplashScreen";
import AuthNavigator from "@/navigation/AuthNavigator";
import AppTabNavigator from "@/navigation/AppTabNavigator";

export default function RootNavigator() {
  const { isAuthenticated, isBootstrapping } = useAuth();

  if (isBootstrapping) {
    return <SplashScreen />;
  }

  return (
    <NavigationContainer>
      {isAuthenticated ? <AppTabNavigator /> : <AuthNavigator />}
    </NavigationContainer>
  );
}
