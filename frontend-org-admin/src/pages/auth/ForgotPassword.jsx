import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { requestPasswordReset } from "@/api/endpoints/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatApiError } from "@/lib/utils";

export default function ForgotPassword() {
  const { t } = useTranslation();
  const [organizationCode, setOrganizationCode] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await requestPasswordReset({ organizationCode, identifier });
      // Always shows the same success state regardless of whether an
      // account was actually found — matches the backend's own
      // always-200 behavior (see auth.services.request_password_reset),
      // which exists so this form can't be used to probe which emails
      // have accounts.
      setSubmitted(true);
    } catch (err) {
      setError(formatApiError(err, t("forgotPassword.genericError")));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("forgotPassword.title")}</CardTitle>
      </CardHeader>
      <CardContent>
        {submitted ? (
          <div className="flex flex-col gap-4">
            <p className="text-sm text-muted-foreground">{t("forgotPassword.submittedMessage")}</p>
            <Link to="/login" className="text-sm text-primary underline underline-offset-4">
              {t("forgotPassword.backToLogin")}
            </Link>
          </div>
        ) : (
          <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
            <p className="text-sm text-muted-foreground">{t("forgotPassword.subtitle")}</p>
            <div className="flex flex-col gap-2">
              <Label htmlFor="organizationCode">{t("login.organizationCode")}</Label>
              <Input
                id="organizationCode"
                placeholder="ABC001"
                value={organizationCode}
                onChange={(e) => setOrganizationCode(e.target.value)}
                required
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="identifier">{t("login.identifier")}</Label>
              <Input
                id="identifier"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                required
              />
            </div>
            {error && (
              <p role="alert" className="text-sm text-destructive">
                {error}
              </p>
            )}
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? t("forgotPassword.submitting") : t("forgotPassword.submit")}
            </Button>
            <Link to="/login" className="text-center text-sm text-primary underline underline-offset-4">
              {t("forgotPassword.backToLogin")}
            </Link>
          </form>
        )}
      </CardContent>
    </Card>
  );
}
