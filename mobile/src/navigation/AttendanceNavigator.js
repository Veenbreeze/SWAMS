import { createNativeStackNavigator } from "@react-navigation/native-stack";
import CheckInScreen from "@/screens/attendance/CheckInScreen";
import HistoryScreen from "@/screens/attendance/HistoryScreen";

const Stack = createNativeStackNavigator();

export default function AttendanceNavigator() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="CheckIn" component={CheckInScreen} />
      <Stack.Screen name="History" component={HistoryScreen} />
    </Stack.Navigator>
  );
}
