import { createContext, useCallback, useEffect, useMemo, useState } from "react";
import {
  changePassword as changePasswordRequest,
  login as loginRequest,
  logout as logoutRequest,
} from "@/api/endpoints/auth";
import { setAuthTokens, clearAuthTokens, setOnAuthExpired } from "@/api/client";

export const AuthContext = createContext(null);

// Tokens are kept in memory only (not localStorage/sessionStorage) per
// docs/01-SYSTEM-ARCHITECTURE.md §6.1 — reduces the XSS token-theft blast
// radius at the cost of losing the session on a hard page refresh, which
// is an accepted trade-off until an httpOnly-cookie refresh flow ships.
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [refreshToken, setRefreshToken] = useState(null);
  const [mustChangePassword, setMustChangePassword] = useState(false);

  const login = useCallback(async (credentials) => {
    const data = await loginRequest(credentials);
    setAuthTokens({ access: data.access_token, refresh: data.refresh_token });
    setRefreshToken(data.refresh_token);
    setUser(data.user);
    setMustChangePassword(Boolean(data.must_change_password));
    return data;
  }, []);

  const completeForcedPasswordChange = useCallback(async ({ currentPassword, newPassword }) => {
    await changePasswordRequest({ currentPassword, newPassword });
    setMustChangePassword(false);
  }, []);

  const updateUser = useCallback((patch) => {
    setUser((current) => (current ? { ...current, ...patch } : current));
  }, []);

  const logout = useCallback(async () => {
    try {
      if (refreshToken) await logoutRequest(refreshToken);
    } finally {
      clearAuthTokens();
      setUser(null);
      setRefreshToken(null);
      setMustChangePassword(false);
    }
  }, [refreshToken]);

  useEffect(() => {
    setOnAuthExpired(() => {
      setUser(null);
      setRefreshToken(null);
    });
  }, []);

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      mustChangePassword,
      login,
      logout,
      completeForcedPasswordChange,
      updateUser,
    }),
    [user, mustChangePassword, login, logout, completeForcedPasswordChange, updateUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
