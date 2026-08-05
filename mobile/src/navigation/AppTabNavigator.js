import { Ionicons } from "@expo/vector-icons";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import DashboardScreen from "@/screens/dashboard/DashboardScreen";
import AttendanceNavigator from "@/navigation/AttendanceNavigator";
import LeaveNavigator from "@/navigation/LeaveNavigator";
import ProfileScreen from "@/screens/profile/ProfileScreen";
import SettingsScreen from "@/screens/settings/SettingsScreen";
import { useI18n } from "@/i18n";
import { colors } from "@/theme/colors";
import { clayRadius, claySurfaceColor } from "@/theme/clay";

const Tab = createBottomTabNavigator();

const TAB_ICONS = {
  Dashboard: "home",
  Attendance: "time",
  Leave: "calendar",
  Profile: "person",
  Settings: "settings",
};

function TabIcon({ route, focused, color, size }) {
  const iconName = TAB_ICONS[route.name] ?? "ellipse";
  return <Ionicons name={focused ? iconName : `${iconName}-outline`} size={size} color={color} />;
}

export default function AppTabNavigator() {
  const { t } = useI18n();
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarLabelStyle: { fontSize: 13, fontWeight: "600" },
        tabBarIconStyle: { marginTop: 2 },
        tabBarStyle: {
          height: 68,
          paddingBottom: 10,
          paddingTop: 10,
          backgroundColor: claySurfaceColor,
          borderTopWidth: 0,
          borderTopLeftRadius: clayRadius.lg,
          borderTopRightRadius: clayRadius.lg,
          shadowColor: "#94a3b8",
          shadowOffset: { width: 0, height: -6 },
          shadowOpacity: 0.25,
          shadowRadius: 14,
          elevation: 12,
        },
        tabBarIcon: ({ focused, color }) => (
          <TabIcon route={route} focused={focused} color={color} size={24} />
        ),
      })}
    >
      <Tab.Screen
        name="Dashboard"
        component={DashboardScreen}
        options={{ tabBarLabel: t("nav.dashboard") }}
      />
      <Tab.Screen
        name="Attendance"
        component={AttendanceNavigator}
        options={{ tabBarLabel: t("nav.attendance") }}
      />
      <Tab.Screen name="Leave" component={LeaveNavigator} options={{ tabBarLabel: t("nav.leave") }} />
      <Tab.Screen
        name="Profile"
        component={ProfileScreen}
        options={{ tabBarLabel: t("nav.profile") }}
      />
      <Tab.Screen
        name="Settings"
        component={SettingsScreen}
        options={{ tabBarLabel: t("nav.settings") }}
      />
    </Tab.Navigator>
  );
}
