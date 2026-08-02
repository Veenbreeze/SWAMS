import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

let accessToken = null;
let refreshToken = null;
let onAuthExpired = () => {};

export function setAuthTokens({ access, refresh }) {
  accessToken = access;
  refreshToken = refresh;
}

export function clearAuthTokens() {
  accessToken = null;
  refreshToken = null;
}

export function setOnAuthExpired(callback) {
  onAuthExpired = callback;
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

    if (response?.status === 401 && code === "TOKEN_EXPIRED" && refreshToken && !config._retried) {
      config._retried = true;
      try {
        refreshPromise =
          refreshPromise ||
          axios.post(`${BASE_URL}/auth/refresh`, { refresh_token: refreshToken });
        const { data } = await refreshPromise;
        refreshPromise = null;
        setAuthTokens({ access: data.access_token, refresh: data.refresh_token });
        config.headers.Authorization = `Bearer ${data.access_token}`;
        return apiClient(config);
      } catch (refreshError) {
        refreshPromise = null;
        clearAuthTokens();
        onAuthExpired();
        return Promise.reject(refreshError);
      }
    }

    if (response?.status === 401 && code === "TOKEN_REUSE_DETECTED") {
      clearAuthTokens();
      onAuthExpired();
    }

    return Promise.reject(
      response?.data?.error || { code: "NETWORK_ERROR", message: error.message }
    );
  }
);

export default apiClient;
