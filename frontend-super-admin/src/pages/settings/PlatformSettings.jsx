import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { getPlatformSettings, updatePlatformSettings } from "@/api/endpoints/platformSettings";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { formatApiError } from "@/lib/utils";

export default function PlatformSettings() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["platform-settings"],
    queryFn: () => getPlatformSettings(),
  });

  const [form, setForm] = useState(null);
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(false);

  if (data && !form) {
    setForm({
      maintenance_mode: data.maintenance_mode,
      default_trial_days: String(data.default_trial_days),
      support_email: data.support_email,
    });
  }

  const mutation = useMutation({
    mutationFn: () =>
      updatePlatformSettings({
        maintenance_mode: form.maintenance_mode,
        default_trial_days: Number(form.default_trial_days),
        support_email: form.support_email,
      }),
    onSuccess: () => {
      setSaved(true);
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["platform-settings"] });
    },
    onError: (err) => setError(formatApiError(err, t("platformSettings.saveError"))),
  });

  function updateField(key, value) {
    setSaved(false);
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <h1 className="font-heading text-2xl font-semibold">{t("nav.platformSettings")}</h1>

      {isLoading && <p className="text-sm text-muted-foreground">{t("platformSettings.loading")}</p>}
      {isError && (
        <p role="alert" className="text-sm text-destructive">
          {t("platformSettings.error")}
        </p>
      )}

      {form && (
        <div className="flex max-w-md flex-col gap-4 rounded-xl border bg-card p-4">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.maintenance_mode}
              onChange={(e) => updateField("maintenance_mode", e.target.checked)}
            />
            {t("platformSettings.maintenanceModeLabel")}
          </label>
          <p className="-mt-2 text-xs text-muted-foreground">
            {t("platformSettings.maintenanceModeHint")}
          </p>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="default-trial-days">{t("platformSettings.defaultTrialDaysLabel")}</Label>
            <Input
              id="default-trial-days"
              type="number"
              min="0"
              value={form.default_trial_days}
              onChange={(e) => updateField("default_trial_days", e.target.value)}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="support-email">{t("platformSettings.supportEmailLabel")}</Label>
            <Input
              id="support-email"
              type="email"
              value={form.support_email}
              onChange={(e) => updateField("support_email", e.target.value)}
            />
          </div>

          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          {saved && <p className="text-sm text-emerald-600">{t("platformSettings.saved")}</p>}

          <Button
            className="self-start"
            disabled={mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? t("common.saving") : t("common.save")}
          </Button>
        </div>
      )}
    </div>
  );
}
