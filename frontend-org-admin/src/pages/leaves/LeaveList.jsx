import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  approveLeaveRequest,
  getLeaveBalance,
  getLeaveRequests,
  rejectLeaveRequest,
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
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const STATUS_FILTERS = [
  { value: "", label: "All" },
  { value: "PENDING", label: "Pending" },
  { value: "APPROVED", label: "Approved" },
  { value: "REJECTED", label: "Rejected" },
  { value: "CANCELLED", label: "Cancelled" },
];

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
  const [status, setStatus] = useState("");
  const [rejectTarget, setRejectTarget] = useState(null);
  const [balanceTarget, setBalanceTarget] = useState(null);
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
        <h1 className="font-heading text-2xl font-semibold">Leaves</h1>
        <div className="flex gap-1">
          {STATUS_FILTERS.map((filter) => (
            <Button
              key={filter.value}
              variant={status === filter.value ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setStatus(filter.value)}
            >
              {filter.label}
            </Button>
          ))}
        </div>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Loading leave requests…</p>}
      {isError && <p className="text-sm text-destructive">Unable to load leave requests.</p>}

      {!isLoading && !isError && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Employee</TableHead>
              <TableHead>Leave type</TableHead>
              <TableHead>Dates</TableHead>
              <TableHead>Days</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {requests.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground">
                  No leave requests found.
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
                    {request.status}
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
                          Approve
                        </Button>
                        <Button size="sm" variant="destructive" onClick={() => setRejectTarget(request)}>
                          Reject
                        </Button>
                      </>
                    )}
                    <Button size="sm" variant="ghost" onClick={() => setBalanceTarget(request)}>
                      Balance
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
    </div>
  );
}

function RejectDialog({ request, onOpenChange, onRejected }) {
  const [reason, setReason] = useState("");
  const [error, setError] = useState(null);

  const rejectMutation = useMutation({
    mutationFn: () => rejectLeaveRequest(request.id, reason),
    onSuccess: () => {
      setReason("");
      setError(null);
      onRejected();
    },
    onError: (err) => setError(err.message || "Unable to reject this request."),
  });

  return (
    <Dialog open={Boolean(request)} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Reject leave request</DialogTitle>
          <DialogDescription>
            {request && `${request.employee_name} — ${request.leave_type_name}`}. A reason is
            required.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-2">
          <Label htmlFor="reject-reason">Reason</Label>
          <textarea
            id="reject-reason"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            className="min-h-20 w-full rounded-lg border border-input bg-transparent px-2.5 py-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
          />
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>

        <DialogFooter>
          <Button
            variant="destructive"
            disabled={!reason.trim() || rejectMutation.isPending}
            onClick={() => rejectMutation.mutate()}
          >
            {rejectMutation.isPending ? "Rejecting…" : "Reject request"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function BalanceDialog({ request, onOpenChange }) {
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
          <DialogTitle>Leave balance</DialogTitle>
          <DialogDescription>{request?.employee_name}</DialogDescription>
        </DialogHeader>

        {isLoading && <p className="text-sm text-muted-foreground">Loading balance…</p>}
        {isError && <p className="text-sm text-destructive">Unable to load leave balance.</p>}

        {!isLoading && !isError && (
          <div className="flex flex-col gap-2">
            {balances.length === 0 && (
              <p className="text-sm text-muted-foreground">No balance records yet.</p>
            )}
            {balances.map((entry) => (
              <div key={entry.id} className="flex items-center justify-between rounded-lg border px-3 py-2">
                <span className="text-sm font-medium">{entry.leave_type_name}</span>
                <span className="text-sm text-muted-foreground">
                  {entry.remaining_days} / {entry.allocated_days} days left
                </span>
              </div>
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
