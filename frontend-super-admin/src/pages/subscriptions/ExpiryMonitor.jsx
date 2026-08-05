import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { getExpiryMonitor } from "@/api/endpoints/subscriptions";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const STATUS_BADGE_VARIANT = {
  TRIAL: "outline",
  ACTIVE: "default",
  EXPIRED: "destructive",
};

function daysUntil(isoDate) {
  const diffMs = new Date(isoDate) - new Date(new Date().toDateString());
  return Math.round(diffMs / (1000 * 60 * 60 * 24));
}

function Urgency({ expiryDate, status }) {
  const { t } = useTranslation();
  const days = daysUntil(expiryDate);
  // `status` only flips to EXPIRED once the daily sweep
  // (apps/subscriptions/tasks.py) next runs, so a lapsed-but-not-yet-swept
  // subscription can still read TRIAL/ACTIVE here with a past expiry date —
  // key off the date itself, not just the status, so it doesn't show a
  // confusing negative day count.
  if (status === "EXPIRED" || days < 0) {
    return <Badge variant="destructive">{t("expiryMonitor.expired")}</Badge>;
  }
  if (days <= 3) {
    return <Badge variant="destructive">{t("expiryMonitor.daysLeft", { count: days })}</Badge>;
  }
  if (days <= 7) {
    return <Badge variant="outline">{t("expiryMonitor.daysLeft", { count: days })}</Badge>;
  }
  return <Badge variant="secondary">{t("expiryMonitor.daysLeft", { count: days })}</Badge>;
}

export default function ExpiryMonitor() {
  const { t } = useTranslation();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["subscriptions", "expiry-monitor"],
    queryFn: getExpiryMonitor,
  });

  const subscriptions = data?.results ?? [];

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="font-heading text-2xl font-semibold">{t("expiryMonitor.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("expiryMonitor.description")}</p>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">{t("expiryMonitor.loading")}</p>}
      {isError && (
        <p role="alert" className="text-sm text-destructive">
          {t("expiryMonitor.error")}
        </p>
      )}

      {!isLoading && !isError && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t("expiryMonitor.table.organization")}</TableHead>
              <TableHead>{t("expiryMonitor.table.plan")}</TableHead>
              <TableHead>{t("expiryMonitor.table.status")}</TableHead>
              <TableHead>{t("expiryMonitor.table.expiryDate")}</TableHead>
              <TableHead>{t("expiryMonitor.table.urgency")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {subscriptions.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">
                  {t("expiryMonitor.noResults")}
                </TableCell>
              </TableRow>
            )}
            {subscriptions.map((subscription) => (
              <TableRow key={subscription.id}>
                <TableCell>
                  {subscription.organization_name} ({subscription.organization_code})
                </TableCell>
                <TableCell>{subscription.plan_name}</TableCell>
                <TableCell>
                  <Badge variant={STATUS_BADGE_VARIANT[subscription.status] ?? "outline"}>
                    {t(`subscriptionStatusLabel.${subscription.status}`, {
                      defaultValue: subscription.status,
                    })}
                  </Badge>
                </TableCell>
                <TableCell>{subscription.expiry_date}</TableCell>
                <TableCell>
                  <Urgency expiryDate={subscription.expiry_date} status={subscription.status} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
