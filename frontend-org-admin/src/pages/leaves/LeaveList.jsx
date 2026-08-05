import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  approveLeaveRequest,
  createLeaveType,
  getLeaveBalance,
  getLeaveRequests,
  getLeaveTypes,
  rejectLeaveRequest,
  updateLeaveType,
} from "@/api/endpoints/leave";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { formatApiError } from "@/lib/utils";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const STATUS_FILTER_VALUES = ["", "PENDING", "APPROVED", "REJECTED", "CANCELLED"];

const STATUS_FILTER_KEYS = {
  "": "leaves.filters.all",
  PENDING: "leaves.filters.pending",
  APPROVED: "leaves.filters.approved",
  REJECTED: "leaves.filters.rejected",
  CANCELLED: "leaves.filters.cancelled",
};

const STATUS_BADGE_VARIANT = {
  PENDING: "outline",
  APPROVED: "default",
  REJECTED: "destructive",
  CANCELLED: "secondary",
};

function formatDate(isoDate) {
  return new Date(isoDate).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export default function LeaveList() {
  const { t } = useTranslation();
  const [status, setStatus] = useState("");
  const [rejectTarget, setRejectTarget] = useState(null);
  const [balanceTarget, setBalanceTarget] = useState(null);
  const [manageTypesOpen, setManageTypesOpen] = useState(false);
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["leave", "requests", status],
    queryFn: () => getLeaveRequests(status ? { status } : undefined),
  });

  const approveMutation = useMutation({
    mutationFn: approveLeaveRequest,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["leave", "requests"] }),
  });

  const requests = data?.results ?? [];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="font-heading text-2xl font-semibold">{t("leaves.title")}</h1>
        <div className="flex items-center gap-2">
          <div className="flex gap-1">
            {STATUS_FILTER_VALUES.map((value) => (
              <Button
                key={value}
                variant={status === value ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setStatus(value)}
              >
                {t(STATUS_FILTER_KEYS[value])}
              </Button>
            ))}
          </div>
          <Button variant="outline" size="sm" onClick={() => setManageTypesOpen(true)}>
            {t("leaves.manageTypes")}
          </Button>
        </div>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">{t("leaves.loading")}</p>}
      {isError && (
        <p role="alert" className="text-sm text-destructive">
          {t("leaves.error")}
        </p>
      )}

      {!isLoading && !isError && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t("leaves.table.employee")}</TableHead>
              <TableHead>{t("leaves.table.leaveType")}</TableHead>
              <TableHead>{t("leaves.table.dates")}</TableHead>
              <TableHead>{t("leaves.table.days")}</TableHead>
              <TableHead>{t("leaves.table.status")}</TableHead>
              <TableHead>{t("leaves.table.actions")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {requests.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground">
                  {t("leaves.noResults")}
                </TableCell>
              </TableRow>
            )}
            {requests.map((request) => (
              <TableRow key={request.id}>
                <TableCell>{request.employee_name}</TableCell>
                <TableCell>{request.leave_type_name}</TableCell>
                <TableCell>
                  {formatDate(request.start_date)} – {formatDate(request.end_date)}
                </TableCell>
                <TableCell>{request.days_requested}</TableCell>
                <TableCell>
                  <Badge variant={STATUS_BADGE_VARIANT[request.status] ?? "outline"}>
                    {t(STATUS_FILTER_KEYS[request.status] ?? "leaves.filters.all")}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className="flex gap-2">
                    {request.status === "PENDING" && (
                      <>
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={approveMutation.isPending}
                          onClick={() => approveMutation.mutate(request.id)}
                        >
                          {t("leaves.approve")}
                        </Button>
                        <Button size="sm" variant="destructive" onClick={() => setRejectTarget(request)}>
                          {t("leaves.reject")}
                        </Button>
                      </>
                    )}
                    <Button size="sm" variant="ghost" onClick={() => setBalanceTarget(request)}>
                      {t("leaves.balance")}
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <RejectDialog
        request={rejectTarget}
        onOpenChange={(open) => !open && setRejectTarget(null)}
        onRejected={() => {
          queryClient.invalidateQueries({ queryKey: ["leave", "requests"] });
          setRejectTarget(null);
        }}
      />

      <BalanceDialog
        request={balanceTarget}
        onOpenChange={(open) => !open && setBalanceTarget(null)}
      />

      <ManageLeaveTypesDialog open={manageTypesOpen} onOpenChange={setManageTypesOpen} />
    </div>
  );
}

function RejectDialog({ request, onOpenChange, onRejected }) {
  const { t } = useTranslation();
  const [reason, setReason] = useState("");
  const [error, setError] = useState(null);

  const rejectMutation = useMutation({
    mutationFn: () => rejectLeaveRequest(request.id, reason),
    onSuccess: () => {
      setReason("");
      setError(null);
      onRejected();
    },
    onError: (err) => setError(formatApiError(err, t("leaves.rejectDialog.genericError"))),
  });

  return (
    <Dialog open={Boolean(request)} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("leaves.rejectDialog.title")}</DialogTitle>
          <DialogDescription>
            {request &&
              t("leaves.rejectDialog.description", {
                employeeName: request.employee_name,
                leaveTypeName: request.leave_type_name,
              })}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-2">
          <Label htmlFor="reject-reason">{t("leaves.rejectDialog.reasonLabel")}</Label>
          <textarea
            id="reject-reason"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            className="min-h-20 w-full rounded-lg border border-input bg-transparent px-2.5 py-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
          />
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="destructive"
            disabled={!reason.trim() || rejectMutation.isPending}
            onClick={() => rejectMutation.mutate()}
          >
            {rejectMutation.isPending
              ? t("leaves.rejectDialog.submitting")
              : t("leaves.rejectDialog.submit")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function BalanceDialog({ request, onOpenChange }) {
  const { t } = useTranslation();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["leave", "balance", request?.employee_id],
    queryFn: () => getLeaveBalance(request.employee_id),
    enabled: Boolean(request),
  });

  const balances = data?.results ?? [];

  return (
    <Dialog open={Boolean(request)} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("leaves.balanceDialog.title")}</DialogTitle>
          <DialogDescription>{request?.employee_name}</DialogDescription>
        </DialogHeader>

        {isLoading && <p className="text-sm text-muted-foreground">{t("leaves.balanceDialog.loading")}</p>}
        {isError && (
          <p role="alert" className="text-sm text-destructive">
            {t("leaves.balanceDialog.error")}
          </p>
        )}

        {!isLoading && !isError && (
          <div className="flex flex-col gap-2">
            {balances.length === 0 && (
              <p className="text-sm text-muted-foreground">{t("leaves.balanceDialog.noResults")}</p>
            )}
            {balances.map((entry) => (
              <div key={entry.id} className="flex items-center justify-between rounded-lg border px-3 py-2">
                <span className="text-sm font-medium">{entry.leave_type_name}</span>
                <span className="text-sm text-muted-foreground">
                  {t("leaves.balanceDialog.daysLeft", {
                    remaining: entry.remaining_days,
                    allocated: entry.allocated_days,
                  })}
                </span>
              </div>
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

function ManageLeaveTypesDialog({ open, onOpenChange }) {
  const { t } = useTranslation();
  const [formTarget, setFormTarget] = useState(null); // null | "create" | leave type object
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["leave", "types"],
    queryFn: () => getLeaveTypes(),
    enabled: open,
  });

  const leaveTypes = data?.results ?? [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("leaves.manageTypesDialog.title")}</DialogTitle>
          <DialogDescription>{t("leaves.manageTypesDialog.description")}</DialogDescription>
        </DialogHeader>

        {isLoading && (
          <p className="text-sm text-muted-foreground">{t("leaves.manageTypesDialog.loading")}</p>
        )}
        {isError && (
          <p role="alert" className="text-sm text-destructive">
            {t("leaves.manageTypesDialog.error")}
          </p>
        )}

        {!isLoading && !isError && (
          <div className="flex flex-col gap-2">
            {leaveTypes.length === 0 && (
              <p className="text-sm text-muted-foreground">{t("leaves.manageTypesDialog.noResults")}</p>
            )}
            {leaveTypes.map((leaveType) => (
              <div
                key={leaveType.id}
                className="flex items-center justify-between rounded-lg border px-3 py-2"
              >
                <div className="flex flex-col">
                  <span className="text-sm font-medium">{leaveType.name}</span>
                  <span className="text-xs text-muted-foreground">
                    {t("leaves.manageTypesDialog.daysPerYear", {
                      days: leaveType.default_annual_days,
                    })}
                  </span>
                </div>
                <Button size="sm" variant="outline" onClick={() => setFormTarget(leaveType)}>
                  {t("common.edit")}
                </Button>
              </div>
            ))}
          </div>
        )}

        <DialogFooter>
          <Button size="sm" onClick={() => setFormTarget("create")}>
            {t("leaves.manageTypesDialog.add")}
          </Button>
        </DialogFooter>
      </DialogContent>

      <LeaveTypeFormDialog
        target={formTarget}
        onOpenChange={(formOpen) => !formOpen && setFormTarget(null)}
        onSaved={() => {
          queryClient.invalidateQueries({ queryKey: ["leave", "types"] });
          setFormTarget(null);
        }}
      />
    </Dialog>
  );
}

function LeaveTypeFormDialog({ target, onOpenChange, onSaved }) {
  const { t } = useTranslation();
  const isEditing = target && target !== "create";
  const [name, setName] = useState("");
  const [defaultAnnualDays, setDefaultAnnualDays] = useState("");
  const [requiresApproval, setRequiresApproval] = useState(true);
  const [error, setError] = useState(null);

  const dialogKey = isEditing ? target.id : target === "create" ? "create" : "closed";
  const [lastKey, setLastKey] = useState(dialogKey);
  if (dialogKey !== lastKey) {
    setLastKey(dialogKey);
    setName(isEditing ? target.name : "");
    setDefaultAnnualDays(isEditing ? String(target.default_annual_days) : "");
    setRequiresApproval(isEditing ? target.requires_approval : true);
    setError(null);
  }

  const mutation = useMutation({
    mutationFn: () => {
      const payload = {
        name,
        default_annual_days: defaultAnnualDays === "" ? 0 : Number(defaultAnnualDays),
        requires_approval: requiresApproval,
      };
      return isEditing ? updateLeaveType(target.id, payload) : createLeaveType(payload);
    },
    onSuccess: onSaved,
    onError: (err) => setError(formatApiError(err, t("leaves.manageTypesDialog.saveError"))),
  });

  return (
    <Dialog open={Boolean(target)} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {isEditing
              ? t("leaves.manageTypesDialog.editTitle")
              : t("leaves.manageTypesDialog.newTitle")}
          </DialogTitle>
        </DialogHeader>

        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="leave-type-name">{t("leaves.manageTypesDialog.nameLabel")}</Label>
            <Input id="leave-type-name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="leave-type-days">{t("leaves.manageTypesDialog.daysLabel")}</Label>
            <Input
              id="leave-type-days"
              type="number"
              min="0"
              value={defaultAnnualDays}
              onChange={(e) => setDefaultAnnualDays(e.target.value)}
            />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={requiresApproval}
              onChange={(e) => setRequiresApproval(e.target.checked)}
            />
            {t("leaves.manageTypesDialog.requiresApprovalLabel")}
          </label>
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button disabled={!name.trim() || mutation.isPending} onClick={() => mutation.mutate()}>
            {mutation.isPending ? t("common.saving") : t("common.save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
