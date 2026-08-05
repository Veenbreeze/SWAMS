import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { I18n } from "i18n-js";
import * as Localization from "expo-localization";
import * as SecureStore from "expo-secure-store";
import en from "./locales/en";
import sw from "./locales/sw";

const LOCALE_KEY = "swams.locale";
const SUPPORTED_LOCALES = ["en", "sw"];

const i18n = new I18n({ en, sw });
i18n.enableFallback = true;
i18n.defaultLocale = "en";

function deviceLocale() {
  const languageCode = Localization.getLocales()[0]?.languageCode;
  return SUPPORTED_LOCALES.includes(languageCode) ? languageCode : "en";
}

const I18nContext = createContext(null);

export function I18nProvider({ children }) {
  const [locale, setLocaleState] = useState(deviceLocale());
  i18n.locale = locale;

  useEffect(() => {
    (async () => {
      const stored = await SecureStore.getItemAsync(LOCALE_KEY);
      if (stored && SUPPORTED_LOCALES.includes(stored)) {
        i18n.locale = stored;
        setLocaleState(stored);
      }
    })();
  }, []);

  const setLocale = useCallback((next) => {
    i18n.locale = next;
    setLocaleState(next);
    SecureStore.setItemAsync(LOCALE_KEY, next);
  }, []);

  const t = useCallback((key, options) => i18n.t(key, options), [locale]);

  const value = useMemo(
    () => ({ locale, setLocale, supportedLocales: SUPPORTED_LOCALES, t }),
    [locale, setLocale, t]
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error("useI18n must be used within I18nProvider");
  }
  return context;
}
