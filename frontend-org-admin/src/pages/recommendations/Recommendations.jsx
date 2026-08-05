import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { getRecommendations } from "@/api/endpoints/recommendations";

function formatDateTime(isoString) {
  return new Date(isoString).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function Recommendations() {
  const { t } = useTranslation();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["recommendations"],
    queryFn: () => getRecommendations(),
  });

  const recommendations = data?.results ?? [];

  return (
    <div className="flex flex-col gap-6 p-6">
      <h1 className="font-heading text-2xl font-semibold">{t("nav.recommendations")}</h1>

      {isLoading && (
        <p className="text-sm text-muted-foreground">{t("recommendations.loading")}</p>
      )}
      {isError && (
        <p role="alert" className="text-sm text-destructive">
          {t("recommendations.error")}
        </p>
      )}

      {!isLoading && !isError && (
        <div className="flex flex-col gap-2">
          {recommendations.length === 0 && (
            <p className="text-sm text-muted-foreground">{t("recommendations.noResults")}</p>
          )}
          {recommendations.map((recommendation) => (
            <div key={recommendation.id} className="flex flex-col gap-1 rounded-xl border bg-card p-4">
              <div className="flex items-center justify-between">
                <p className="font-medium">{recommendation.employee_name}</p>
                <p className="text-xs text-muted-foreground">
                  {formatDateTime(recommendation.created_at)}
                </p>
              </div>
              <p className="text-sm text-muted-foreground">{recommendation.message}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
