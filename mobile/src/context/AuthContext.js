import { createContext, useCallback, useEffect, useMemo, useState } from "react";
import {
  login as loginRequest,
  logout as logoutRequest,
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
      await hydrateTokens();
      // A token surviving app restart doesn't mean the session is still
      // valid server-side; Phase 2 adds a "who am I" call here to
      // rehydrate `user` from a stored access token instead of just
      // leaving it logged-out-looking until the next explicit login.
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
    setUser(data.user);
    setMustChangePassword(Boolean(data.must_change_password));
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
