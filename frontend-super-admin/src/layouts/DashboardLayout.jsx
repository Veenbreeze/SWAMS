import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Menu, X } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import LanguageSwitcher from "@/components/LanguageSwitcher";
import ProfileDialog from "@/components/ProfileDialog";

const NAV_ITEMS = [
  { to: "/dashboard", labelKey: "nav.dashboard" },
  { to: "/organizations", labelKey: "nav.organizations" },
  { to: "/subscriptions", labelKey: "nav.subscriptionPlans" },
  { to: "/subscriptions/expiry", labelKey: "nav.expiryMonitor" },
  { to: "/audit-logs", labelKey: "nav.auditLogs" },
  { to: "/security", labelKey: "nav.securityEvents" },
  { to: "/settings", labelKey: "nav.platformSettings" },
];

export default function DashboardLayout() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const [profileOpen, setProfileOpen] = useState(false);
  const [navOpen, setNavOpen] = useState(false);

  return (
    <div className="flex min-h-svh">
      {/* Below lg, the sidebar is an off-canvas drawer (fixed, slides in)
          instead of taking up permanent width — a 256px rail plus content
          doesn't fit a phone viewport. At lg+ it reverts to the original
          sticky, always-visible layout. */}
      {navOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/40 lg:hidden"
          onClick={() => setNavOpen(false)}
          aria-hidden="true"
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-30 flex h-svh w-64 shrink-0 flex-col bg-sidebar p-4 text-sidebar-foreground transition-transform duration-200 lg:sticky lg:top-0 lg:translate-x-0 ${
          navOpen ? "translate-x-0" : "-translate-x-full"
        }`}
        style={{ boxShadow: "var(--clay-shadow-sidebar-edge)" }}
      >
        <div className="mb-6 flex items-center justify-between px-2">
          <span className="text-lg font-semibold text-brand-secondary">SWAMS — Platform</span>
          <button
            type="button"
            className="rounded-lg p-1 text-sidebar-foreground/70 hover:bg-sidebar-accent lg:hidden"
            onClick={() => setNavOpen(false)}
          >
            <X size={18} />
          </button>
        </div>
        <nav className="flex flex-col gap-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={() => setNavOpen(false)}
              className={({ isActive }) =>
                `rounded-xl px-3 py-2 text-sm transition-all ${
                  isActive
                    ? "bg-sidebar-primary text-sidebar-primary-foreground"
                    : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                }`
              }
              style={({ isActive }) =>
                isActive ? { boxShadow: "var(--clay-shadow-nav-active)" } : undefined
              }
            >
              {t(item.labelKey)}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="clay-raised-sm relative z-10 flex items-center justify-between gap-2 rounded-none bg-card px-4 py-3 sm:px-6">
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted lg:hidden"
              onClick={() => setNavOpen(true)}
            >
              <Menu size={20} />
            </button>
            <button
              type="button"
              className="flex items-center gap-2 rounded-full outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
              onClick={() => setProfileOpen(true)}
            >
              <Avatar src={user?.profile_picture_url} name={user?.email} className="size-7" />
              <span className="hidden text-sm text-muted-foreground sm:inline">{user?.email}</span>
            </button>
          </div>
          <div className="flex items-center gap-2 sm:gap-3">
            <LanguageSwitcher />
            <Button variant="outline" size="sm" onClick={logout}>
              {t("common.logOut")}
            </Button>
          </div>
        </header>
        <main className="flex-1 overflow-x-hidden overflow-y-auto bg-background p-4 sm:p-6">
          <Outlet />
        </main>
      </div>

      <ProfileDialog open={profileOpen} onOpenChange={setProfileOpen} />
    </div>
  );
}
