import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatApiError } from "@/lib/utils";

export default function ForceChangePassword() {
  const { t } = useTranslation();
  const { completeForcedPasswordChange } = useAuth();
  const navigate = useNavigate();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);

    if (!currentPassword || !newPassword) {
      setError(t("forceChangePassword.validationError"));
      return;
    }
    if (newPassword !== confirmPassword) {
      setError(t("forceChangePassword.mismatchError"));
      return;
    }

    setIsSubmitting(true);
    try {
      await completeForcedPasswordChange({ currentPassword, newPassword });
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(formatApiError(err, t("forceChangePassword.genericError")));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("forceChangePassword.title")}</CardTitle>
      </CardHeader>
      <CardContent>
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <p className="text-sm text-muted-foreground">{t("forceChangePassword.subtitle")}</p>
          <div className="flex flex-col gap-2">
            <Label htmlFor="currentPassword">{t("forceChangePassword.currentPassword")}</Label>
            <Input
              id="currentPassword"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="newPassword">{t("forceChangePassword.newPassword")}</Label>
            <Input
              id="newPassword"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="confirmPassword">{t("forceChangePassword.confirmPassword")}</Label>
            <Input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </div>
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? t("common.saving") : t("forceChangePassword.submit")}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
