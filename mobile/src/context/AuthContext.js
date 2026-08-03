import { createContext, useCallback, useEffect, useMemo, useState } from "react";
import {
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
    }),
    [user, mustChangePassword, isBootstrapping, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
