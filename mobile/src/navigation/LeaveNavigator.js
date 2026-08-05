import { createNativeStackNavigator } from "@react-navigation/native-stack";
import LeaveRequestScreen from "@/screens/leave/LeaveRequestScreen";
import LeaveHistoryScreen from "@/screens/leave/LeaveHistoryScreen";

const Stack = createNativeStackNavigator();

export default function LeaveNavigator() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="LeaveRequest" component={LeaveRequestScreen} />
      <Stack.Screen name="LeaveHistory" component={LeaveHistoryScreen} />
    </Stack.Navigator>
  );
}
