import axios from "axios";
import { loadTokens, saveTokens, clearTokens } from "@/storage/secureStore";

const BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

let accessToken = null;
let onAuthExpired = () => {};

export function setOnAuthExpired(callback) {
  onAuthExpired = callback;
}

export async function hydrateTokens() {
  const { access } = await loadTokens();
  accessToken = access;
  return access;
}

export async function persistTokens({ access, refresh }) {
  accessToken = access;
  await saveTokens({ access, refresh });
}

export async function forgetTokens() {
  accessToken = null;
  await clearTokens();
}

apiClient.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

let refreshPromise = null;

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error;
    const code = response?.data?.error?.code;

    if (response?.status === 401 && code === "TOKEN_EXPIRED" && !config._retried) {
      config._retried = true;
      try {
        const { refresh } = await loadTokens();
        if (!refresh) throw new Error("No refresh token available");

        refreshPromise =
          refreshPromise || axios.post(`${BASE_URL}/auth/refresh`, { refresh_token: refresh });
        const { data } = await refreshPromise;
        refreshPromise = null;
        await persistTokens({ access: data.access_token, refresh: data.refresh_token });
        config.headers.Authorization = `Bearer ${data.access_token}`;
        return apiClient(config);
      } catch (refreshError) {
        refreshPromise = null;
        await forgetTokens();
        onAuthExpired();
        return Promise.reject(refreshError);
      }
    }

    if (response?.status === 401 && code === "TOKEN_REUSE_DETECTED") {
      await forgetTokens();
      onAuthExpired();
    }

    return Promise.reject(
      response?.data?.error || { code: "NETWORK_ERROR", message: error.message }
    );
  }
);

export default apiClient;
