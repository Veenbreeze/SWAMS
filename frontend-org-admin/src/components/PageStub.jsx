import { useTranslation } from "react-i18next";

// Placeholder for pages built in later phases (see docs/05-DEVELOPMENT-ROADMAP.md).
export default function PageStub({ title }) {
  const { t } = useTranslation();
  return (
    <div>
      <h1 className="text-2xl font-semibold">{title}</h1>
      <p className="mt-2 text-sm text-muted-foreground">{t("pageStub.comingSoon")}</p>
    </div>
  );
}
