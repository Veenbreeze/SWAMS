import { createBrowserRouter, Navigate } from "react-router-dom";
import ProtectedRoute from "@/routes/ProtectedRoute";
import AuthLayout from "@/layouts/AuthLayout";
import DashboardLayout from "@/layouts/DashboardLayout";
import Login from "@/pages/auth/Login";
import ForceChangePassword from "@/pages/auth/ForceChangePassword";
import Dashboard from "@/pages/dashboard/Dashboard";
import OrganizationList from "@/pages/organizations/OrganizationList";
import PlanList from "@/pages/subscriptions/PlanList";
import AuditLogViewer from "@/pages/audit-logs/AuditLogViewer";
import SecurityEvents from "@/pages/security/SecurityEvents";
import PlatformSettings from "@/pages/settings/PlatformSettings";

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
          { path: "/organizations", element: <OrganizationList /> },
          { path: "/subscriptions", element: <PlanList /> },
          { path: "/audit-logs", element: <AuditLogViewer /> },
          { path: "/security", element: <SecurityEvents /> },
          { path: "/settings", element: <PlatformSettings /> },
        ],
      },
    ],
  },
  { path: "/", element: <Navigate to="/dashboard" replace /> },
  { path: "*", element: <Navigate to="/dashboard" replace /> },
]);
