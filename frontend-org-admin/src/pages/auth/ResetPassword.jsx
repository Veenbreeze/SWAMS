import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { confirmPasswordReset } from "@/api/endpoints/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatApiError } from "@/lib/utils";

export default function ResetPassword() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const uid = searchParams.get("uid");
  const token = searchParams.get("token");

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  if (!uid || !token) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t("resetPassword.title")}</CardTitle>
        </CardHeader>
        <CardContent>
          <p role="alert" className="text-sm text-destructive">
            {t("resetPassword.invalidLinkError")}
          </p>
          <Link
            to="/forgot-password"
            className="mt-4 block text-center text-sm text-primary underline underline-offset-4"
          >
            {t("resetPassword.requestNewLink")}
          </Link>
        </CardContent>
      </Card>
    );
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);

    if (!newPassword) {
      setError(t("resetPassword.validationError"));
      return;
    }
    if (newPassword !== confirmPassword) {
      setError(t("resetPassword.mismatchError"));
      return;
    }

    setIsSubmitting(true);
    try {
      await confirmPasswordReset({ uid, token, newPassword });
      setDone(true);
      setTimeout(() => navigate("/login", { replace: true }), 2000);
    } catch (err) {
      setError(formatApiError(err, t("resetPassword.genericError")));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("resetPassword.title")}</CardTitle>
      </CardHeader>
      <CardContent>
        {done ? (
          <p className="text-sm text-primary">{t("resetPassword.successMessage")}</p>
        ) : (
          <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
            <p className="text-sm text-muted-foreground">{t("resetPassword.subtitle")}</p>
            <div className="flex flex-col gap-2">
              <Label htmlFor="newPassword">{t("resetPassword.newPassword")}</Label>
              <Input
                id="newPassword"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="confirmPassword">{t("resetPassword.confirmPassword")}</Label>
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
              {isSubmitting ? t("common.saving") : t("resetPassword.submit")}
            </Button>
          </form>
        )}
      </CardContent>
    </Card>
  );
}
