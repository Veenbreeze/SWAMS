import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  getNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "@/api/endpoints/notifications";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const selectClassName =
  "h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

function formatDateTime(isoString) {
  return new Date(isoString).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function Notifications() {
  const { t } = useTranslation();
  const [filter, setFilter] = useState("");
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["notifications", filter],
    queryFn: () => getNotifications(filter ? { is_read: filter === "read" } : undefined),
  });

  const markReadMutation = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });
  const markAllReadMutation = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const notifications = data?.results ?? [];

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="font-heading text-2xl font-semibold">{t("nav.notifications")}</h1>
        <div className="flex items-center gap-3">
          <select
            className={selectClassName}
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="">{t("notifications.filters.all")}</option>
            <option value="unread">{t("notifications.filters.unread")}</option>
            <option value="read">{t("notifications.filters.read")}</option>
          </select>
          <Button
            size="sm"
            variant="outline"
            disabled={markAllReadMutation.isPending}
            onClick={() => markAllReadMutation.mutate()}
          >
            {t("notifications.markAllRead")}
          </Button>
        </div>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">{t("notifications.loading")}</p>}
      {isError && (
        <p role="alert" className="text-sm text-destructive">
          {t("notifications.error")}
        </p>
      )}

      {!isLoading && !isError && (
        <div className="flex flex-col gap-2">
          {notifications.length === 0 && (
            <p className="text-sm text-muted-foreground">{t("notifications.noResults")}</p>
          )}
          {notifications.map((notification) => (
            <div
              key={notification.id}
              className={`flex items-start justify-between gap-4 rounded-xl border p-4 ${
                notification.is_read ? "bg-card" : "bg-accent/40"
              }`}
            >
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <Badge variant="outline">{notification.category}</Badge>
                  {!notification.is_read && <Badge variant="default">{t("notifications.new")}</Badge>}
                </div>
                <p className="font-medium">{notification.title}</p>
                {notification.message && (
                  <p className="text-sm text-muted-foreground">{notification.message}</p>
                )}
                <p className="text-xs text-muted-foreground">{formatDateTime(notification.created_at)}</p>
              </div>
              {!notification.is_read && (
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={markReadMutation.isPending}
                  onClick={() => markReadMutation.mutate(notification.id)}
                >
                  {t("notifications.markRead")}
                </Button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
