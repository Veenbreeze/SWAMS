import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/organizations", label: "Organizations" },
  { to: "/subscriptions", label: "Subscription Plans" },
  { to: "/audit-logs", label: "Audit Logs" },
  { to: "/security", label: "Security Events" },
  { to: "/settings", label: "Platform Settings" },
];

export default function DashboardLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="flex min-h-svh">
      <aside className="w-64 shrink-0 border-r bg-card p-4">
        <div className="mb-6 px-2 text-lg font-semibold">SWAMS — Platform</div>
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
          <span className="text-sm text-muted-foreground">{user?.email}</span>
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
