import { useTranslation } from "react-i18next";

const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "sw", label: "Kiswahili" },
];

export default function LanguageSwitcher() {
  const { i18n } = useTranslation();

  return (
    <select
      aria-label="Language"
      value={i18n.resolvedLanguage}
      onChange={(event) => i18n.changeLanguage(event.target.value)}
      className="h-8 rounded-lg border border-input bg-transparent px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
    >
      {LANGUAGES.map((language) => (
        <option key={language.code} value={language.code}>
          {language.label}
        </option>
      ))}
    </select>
  );
}
