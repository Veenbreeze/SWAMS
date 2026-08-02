import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";

// UX-level guard only. The backend re-validates identity, tenant ownership,
// and role on every request — this component just avoids flashing admin
// screens at an unauthenticated visitor (docs/01-SYSTEM-ARCHITECTURE.md §6.2).
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
