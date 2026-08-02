import { createBrowserRouter, Navigate } from "react-router-dom";
import ProtectedRoute from "@/routes/ProtectedRoute";
import AuthLayout from "@/layouts/AuthLayout";
import DashboardLayout from "@/layouts/DashboardLayout";
import Login from "@/pages/auth/Login";
import ForceChangePassword from "@/pages/auth/ForceChangePassword";
import Dashboard from "@/pages/dashboard/Dashboard";
import EmployeeList from "@/pages/employees/EmployeeList";
import DepartmentList from "@/pages/departments/DepartmentList";
import BranchList from "@/pages/branches/BranchList";
import AttendanceList from "@/pages/attendance/AttendanceList";
import Reports from "@/pages/reports/Reports";
import LeaveList from "@/pages/leaves/LeaveList";
import Notifications from "@/pages/notifications/Notifications";
import Settings from "@/pages/settings/Settings";

export const router = createBrowserRouter([
  {
    element: <AuthLayout />,
    children: [
      { path: "/login", element: <Login /> },
      { path: "/force-change-password", element: <ForceChangePassword /> },
    ],
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <DashboardLayout />,
        children: [
          { path: "/dashboard", element: <Dashboard /> },
          { path: "/employees", element: <EmployeeList /> },
          { path: "/departments", element: <DepartmentList /> },
          { path: "/branches", element: <BranchList /> },
          { path: "/attendance", element: <AttendanceList /> },
          { path: "/reports", element: <Reports /> },
          { path: "/leaves", element: <LeaveList /> },
          { path: "/notifications", element: <Notifications /> },
          { path: "/settings", element: <Settings /> },
        ],
      },
    ],
  },
  { path: "/", element: <Navigate to="/dashboard" replace /> },
  { path: "*", element: <Navigate to="/dashboard" replace /> },
]);
