import { createNativeStackNavigator } from "@react-navigation/native-stack";
import CheckInScreen from "@/screens/attendance/CheckInScreen";
import HistoryScreen from "@/screens/attendance/HistoryScreen";

const Stack = createNativeStackNavigator();

export default function AttendanceNavigator() {
  return (
    <Stack.Navigator>
      <Stack.Screen name="CheckIn" component={CheckInScreen} options={{ title: "Attendance" }} />
      <Stack.Screen name="History" component={HistoryScreen} options={{ title: "History" }} />
    </Stack.Navigator>
  );
}
