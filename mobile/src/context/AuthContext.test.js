import { renderHook, waitFor, act } from "@testing-library/react-native";
import { useContext } from "react";
import { AuthContext, AuthProvider } from "@/context/AuthContext";

jest.mock("@/services/api/endpoints/auth", () => ({
  login: jest.fn(),
  logout: jest.fn(),
  me: jest.fn(),
  changePassword: jest.fn(),
}));
jest.mock("@/services/api/client", () => ({
  persistTokens: jest.fn(),
  forgetTokens: jest.fn(),
  hydrateTokens: jest.fn(),
  setOnAuthExpired: jest.fn(),
}));
jest.mock("@/storage/secureStore", () => ({
  loadTokens: jest.fn(),
}));

const authApi = require("@/services/api/endpoints/auth");
const client = require("@/services/api/client");
const secureStore = require("@/storage/secureStore");

function renderAuth() {
  // RNTL v14's `renderHook` is async (it awaits a full render pass), unlike
  // web `@testing-library/react`'s synchronous version — every call site
  // below must `await` it.
  return renderHook(() => useContext(AuthContext), { wrapper: AuthProvider });
}

beforeEach(() => {
  jest.clearAllMocks();
  client.hydrateTokens.mockResolvedValue(null);
});

describe("AuthContext", () => {
  it("finishes bootstrapping unauthenticated when no token was stored", async () => {
    const { result } = await renderAuth();

    await waitFor(() => expect(result.current.isBootstrapping).toBe(false));

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.mustChangePassword).toBe(false);
  });

  it("sets the user after a successful login that doesn't require a password change", async () => {
    authApi.login.mockResolvedValue({
      access_token: "access",
      refresh_token: "refresh",
      must_change_password: false,
      user: { id: "u1", email: "admin@example.com" },
    });
    const { result } = await renderAuth();
    await waitFor(() => expect(result.current.isBootstrapping).toBe(false));

    await act(async () => {
      await result.current.login({ identifier: "admin@example.com", password: "pw" });
    });

    expect(client.persistTokens).toHaveBeenCalledWith({ access: "access", refresh: "refresh" });
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.mustChangePassword).toBe(false);
  });

  it("sets mustChangePassword without authenticating when the server requires it", async () => {
    authApi.login.mockResolvedValue({
      access_token: "access",
      refresh_token: "refresh",
      must_change_password: true,
      user: { id: "u1", email: "temp@example.com" },
    });
    const { result } = await renderAuth();
    await waitFor(() => expect(result.current.isBootstrapping).toBe(false));

    await act(async () => {
      await result.current.login({ identifier: "temp@example.com", password: "temp-pw" });
    });

    expect(result.current.mustChangePassword).toBe(true);
    // `user` must stay unset — see AuthContext.js's comment on why setting it
    // here would skip past the forced-password-change screen entirely.
    expect(result.current.isAuthenticated).toBe(false);
  });

  it("clears tokens and user state on logout", async () => {
    authApi.login.mockResolvedValue({
      access_token: "access",
      refresh_token: "refresh",
      must_change_password: false,
      user: { id: "u1", email: "admin@example.com" },
    });
    secureStore.loadTokens.mockResolvedValue({ access: "access", refresh: "refresh" });
    const { result } = await renderAuth();
    await waitFor(() => expect(result.current.isBootstrapping).toBe(false));
    await act(async () => {
      await result.current.login({ identifier: "admin@example.com", password: "pw" });
    });

    await act(async () => {
      await result.current.logout();
    });

    expect(authApi.logout).toHaveBeenCalledWith("refresh");
    expect(client.forgetTokens).toHaveBeenCalled();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it("completeForcedPasswordChange clears the flag and authenticates the user", async () => {
    authApi.login.mockResolvedValue({
      access_token: "access",
      refresh_token: "refresh",
      must_change_password: true,
      user: { id: "u1", email: "temp@example.com" },
    });
    authApi.changePassword.mockResolvedValue({});
    authApi.me.mockResolvedValue({ id: "u1", email: "temp@example.com", employee: null });
    const { result } = await renderAuth();
    await waitFor(() => expect(result.current.isBootstrapping).toBe(false));
    await act(async () => {
      await result.current.login({ identifier: "temp@example.com", password: "temp-pw" });
    });
    expect(result.current.mustChangePassword).toBe(true);

    await act(async () => {
      await result.current.completeForcedPasswordChange({
        currentPassword: "temp-pw",
        newPassword: "NewSecurePass1!",
      });
    });

    expect(authApi.changePassword).toHaveBeenCalledWith({
      currentPassword: "temp-pw",
      newPassword: "NewSecurePass1!",
    });
    expect(result.current.mustChangePassword).toBe(false);
    expect(result.current.isAuthenticated).toBe(true);
  });

  it("changePassword calls the API without touching auth state", async () => {
    authApi.login.mockResolvedValue({
      access_token: "access",
      refresh_token: "refresh",
      must_change_password: false,
      user: { id: "u1", email: "admin@example.com" },
    });
    authApi.changePassword.mockResolvedValue({});
    const { result } = await renderAuth();
    await waitFor(() => expect(result.current.isBootstrapping).toBe(false));
    await act(async () => {
      await result.current.login({ identifier: "admin@example.com", password: "pw" });
    });

    await act(async () => {
      await result.current.changePassword({
        currentPassword: "pw",
        newPassword: "NewSecurePass1!",
      });
    });

    expect(authApi.changePassword).toHaveBeenCalledWith({
      currentPassword: "pw",
      newPassword: "NewSecurePass1!",
    });
    expect(result.current.mustChangePassword).toBe(false);
    expect(result.current.isAuthenticated).toBe(true);
  });

  it("updateEmployee merges a patch into user.employee without a re-login", async () => {
    authApi.login.mockResolvedValue({
      access_token: "access",
      refresh_token: "refresh",
      must_change_password: false,
      user: {
        id: "u1",
        email: "employee@example.com",
        employee: { id: "e1", first_name: "Amina", phone: "", profile_picture_url: "" },
      },
    });
    const { result } = await renderAuth();
    await waitFor(() => expect(result.current.isBootstrapping).toBe(false));
    await act(async () => {
      await result.current.login({ identifier: "employee@example.com", password: "pw" });
    });

    await act(async () => {
      result.current.updateEmployee({ profile_picture_url: "https://example.com/new.jpg" });
    });

    expect(result.current.user.employee.profile_picture_url).toBe(
      "https://example.com/new.jpg"
    );
    // Untouched fields survive the merge.
    expect(result.current.user.employee.first_name).toBe("Amina");
  });
});
