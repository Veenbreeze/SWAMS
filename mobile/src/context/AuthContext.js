import { createContext, useCallback, useEffect, useMemo, useState } from "react";
import {
  changePassword as changePasswordRequest,
  login as loginRequest,
  logout as logoutRequest,
  me as meRequest,
} from "@/services/api/endpoints/auth";
import { persistTokens, forgetTokens, hydrateTokens, setOnAuthExpired } from "@/services/api/client";
import { loadTokens } from "@/storage/secureStore";

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [mustChangePassword, setMustChangePassword] = useState(false);
  const [isBootstrapping, setIsBootstrapping] = useState(true);

  useEffect(() => {
    (async () => {
      const access = await hydrateTokens();
      if (access) {
        // A token surviving app restart doesn't mean the session is still
        // valid server-side (it may have been revoked, or the account
        // suspended) — rehydrate `user` from the server rather than
        // trusting the token's mere presence. A stale/expired access
        // token here is fine: the client's response interceptor silently
        // refreshes it and retries this call.
        try {
          setUser(await meRequest());
        } catch (error) {
          if (error?.code === "MUST_CHANGE_PASSWORD") {
            setMustChangePassword(true);
          } else {
            await forgetTokens();
          }
        }
      }
      setIsBootstrapping(false);
    })();
  }, []);

  useEffect(() => {
    setOnAuthExpired(() => {
      setUser(null);
    });
  }, []);

  const login = useCallback(async (credentials) => {
    const data = await loginRequest(credentials);
    await persistTokens({ access: data.access_token, refresh: data.refresh_token });
    // `user` stays unset while a password change is still required: every
    // endpoint but change-password is server-side blocked until then (see
    // docs/01-SYSTEM-ARCHITECTURE.md §6.1), and `isAuthenticated` gates
    // RootNavigator into AppTabNavigator — setting `user` here too would
    // skip past AuthNavigator's ForceChangePasswordScreen entirely.
    if (data.must_change_password) {
      setMustChangePassword(true);
    } else {
      setUser(data.user);
    }
    return data;
  }, []);

  // Used by ForceChangePasswordScreen: the server accepts the request
  // (change-password is the one endpoint that stays open while
  // `must_change_password` is set — see Architecture §6.1), then this
  // clears the flag and rehydrates `user` so the app transitions straight
  // into AppTabNavigator without a second login.
  const completeForcedPasswordChange = useCallback(async ({ currentPassword, newPassword }) => {
    await changePasswordRequest({ currentPassword, newPassword });
    const freshUser = await meRequest();
    setUser(freshUser);
    setMustChangePassword(false);
  }, []);

  // Voluntary change from SettingsScreen — unlike completeForcedPasswordChange,
  // this doesn't touch `mustChangePassword` (it's already false whenever
  // Settings is reachable) or need to rehydrate `user`, since nothing
  // about the account's auth state changes besides the password itself.
  const changePassword = useCallback(async ({ currentPassword, newPassword }) => {
    await changePasswordRequest({ currentPassword, newPassword });
  }, []);

  // Lets screens that mutate the employee's own record (ProfileScreen's
  // picture/phone edits) push the change into shared state immediately —
  // without this, DashboardScreen and anywhere else reading `user.employee`
  // would keep showing stale data until the next full `/auth/me` refetch
  // (app restart or re-login), since nothing else here invalidates it.
  const updateEmployee = useCallback((patch) => {
    setUser((current) =>
      current?.employee ? { ...current, employee: { ...current.employee, ...patch } } : current
    );
  }, []);

  const logout = useCallback(async () => {
    try {
      const { refresh } = await loadTokens();
      if (refresh) await logoutRequest(refresh);
    } finally {
      await forgetTokens();
      setUser(null);
      setMustChangePassword(false);
    }
  }, []);

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      mustChangePassword,
      isBootstrapping,
      login,
      logout,
      completeForcedPasswordChange,
      changePassword,
      updateEmployee,
    }),
    [
      user,
      mustChangePassword,
      isBootstrapping,
      login,
      logout,
      completeForcedPasswordChange,
      changePassword,
      updateEmployee,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
