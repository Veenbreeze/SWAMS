import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";

// UX-level guard only. The backend re-validates identity and role on every
// request — see docs/01-SYSTEM-ARCHITECTURE.md §6.2.
export default function ProtectedRoute() {
  const { isAuthenticated, mustChangePassword } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (mustChangePassword) {
    return <Navigate to="/force-change-password" replace />;
  }

  return <Outlet />;
}
