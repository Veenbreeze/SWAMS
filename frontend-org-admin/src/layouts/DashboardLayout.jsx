import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/employees", label: "Employees" },
  { to: "/departments", label: "Departments" },
  { to: "/branches", label: "Branches" },
  { to: "/attendance", label: "Attendance" },
  { to: "/reports", label: "Reports" },
  { to: "/leaves", label: "Leaves" },
  { to: "/notifications", label: "Notifications" },
  { to: "/settings", label: "Settings" },
];

export default function DashboardLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="flex min-h-svh">
      <aside className="w-60 shrink-0 border-r bg-card p-4">
        <div className="mb-6 px-2 text-lg font-semibold">SWAMS</div>
        <nav className="flex flex-col gap-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `rounded-md px-3 py-2 text-sm ${
                  isActive ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:bg-accent"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex flex-1 flex-col">
        <header className="flex items-center justify-between border-b px-6 py-3">
          <span className="text-sm text-muted-foreground">{user?.employee?.first_name ?? user?.email}</span>
          <Button variant="outline" size="sm" onClick={logout}>
            Log out
          </Button>
        </header>
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
