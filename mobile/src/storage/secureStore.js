import * as SecureStore from "expo-secure-store";

const ACCESS_TOKEN_KEY = "swams.accessToken";
const REFRESH_TOKEN_KEY = "swams.refreshToken";

export async function saveTokens({ access, refresh }) {
  await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, access);
  await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, refresh);
}

export async function loadTokens() {
  const [access, refresh] = await Promise.all([
    SecureStore.getItemAsync(ACCESS_TOKEN_KEY),
    SecureStore.getItemAsync(REFRESH_TOKEN_KEY),
  ]);
  return { access, refresh };
}

export async function clearTokens() {
  await Promise.all([
    SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY),
    SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY),
  ]);
}
