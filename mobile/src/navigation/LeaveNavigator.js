import { createNativeStackNavigator } from "@react-navigation/native-stack";
import LeaveRequestScreen from "@/screens/leave/LeaveRequestScreen";
import LeaveHistoryScreen from "@/screens/leave/LeaveHistoryScreen";

const Stack = createNativeStackNavigator();

export default function LeaveNavigator() {
  return (
    <Stack.Navigator>
      <Stack.Screen
        name="LeaveRequest"
        component={LeaveRequestScreen}
        options={{ title: "Request Leave" }}
      />
      <Stack.Screen
        name="LeaveHistory"
        component={LeaveHistoryScreen}
        options={{ title: "Leave History" }}
      />
    </Stack.Navigator>
  );
}
