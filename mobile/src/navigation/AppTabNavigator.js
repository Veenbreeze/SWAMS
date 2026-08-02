import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import DashboardScreen from "@/screens/dashboard/DashboardScreen";
import AttendanceNavigator from "@/navigation/AttendanceNavigator";
import LeaveNavigator from "@/navigation/LeaveNavigator";
import ProfileScreen from "@/screens/profile/ProfileScreen";
import SettingsScreen from "@/screens/settings/SettingsScreen";

const Tab = createBottomTabNavigator();

export default function AppTabNavigator() {
  return (
    <Tab.Navigator screenOptions={{ headerShown: false }}>
      <Tab.Screen name="Dashboard" component={DashboardScreen} />
      <Tab.Screen name="Attendance" component={AttendanceNavigator} />
      <Tab.Screen name="Leave" component={LeaveNavigator} />
      <Tab.Screen name="Profile" component={ProfileScreen} />
      <Tab.Screen name="Settings" component={SettingsScreen} />
    </Tab.Navigator>
  );
}
