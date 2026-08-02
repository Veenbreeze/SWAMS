import { createNativeStackNavigator } from "@react-navigation/native-stack";
import LoginScreen from "@/screens/auth/LoginScreen";
import ForceChangePasswordScreen from "@/screens/auth/ForceChangePasswordScreen";
import { useAuth } from "@/hooks/useAuth";

const Stack = createNativeStackNavigator();

export default function AuthNavigator() {
  const { mustChangePassword } = useAuth();

  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      {mustChangePassword ? (
        <Stack.Screen name="ForceChangePassword" component={ForceChangePasswordScreen} />
      ) : (
        <Stack.Screen name="Login" component={LoginScreen} />
      )}
    </Stack.Navigator>
  );
}
