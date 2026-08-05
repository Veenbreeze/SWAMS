import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

// In-app replacement for window.confirm() — every destructive/confirming
// action (delete, terminate, suspend, reset password, ...) goes through
// this instead of the browser's native confirm popup, so the prompt
// matches the rest of the UI instead of looking like a browser alert.
export default function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  destructive = true,
  isPending = false,
  onConfirm,
  onCancel,
}) {
  const { t } = useTranslation();

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onCancel()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={onCancel} disabled={isPending}>
            {t("common.cancel")}
          </Button>
          <Button
            variant={destructive ? "destructive" : "default"}
            onClick={onConfirm}
            disabled={isPending}
          >
            {isPending ? t("common.saving") : confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
