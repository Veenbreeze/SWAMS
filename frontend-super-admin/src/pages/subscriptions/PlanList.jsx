import { cloneElement, useId, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { getOrganizations } from "@/api/endpoints/organizations";
import {
  assignSubscription,
  cancelSubscription,
  createPlan,
  getPlans,
  getSubscriptions,
  updatePlan,
} from "@/api/endpoints/subscriptions";
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

const STATUS_BADGE_VARIANT = {
  TRIAL: "outline",
  ACTIVE: "default",
  EXPIRED: "destructive",
  CANCELLED: "secondary",
};

const selectClassName =
  "clay-inset h-8 w-full min-w-0 rounded-xl border border-transparent bg-transparent px-2.5 py-1 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

export default function PlanList() {
  const { t } = useTranslation();
  const [planDialog, setPlanDialog] = useState(null); // null | "create" | plan object (edit)
  const [isAssignOpen, setIsAssignOpen] = useState(false);
  const queryClient = useQueryClient();

  const plansQuery = useQuery({ queryKey: ["subscription-plans"], queryFn: getPlans });
  const subscriptionsQuery = useQuery({
    queryKey: ["subscriptions"],
    queryFn: () => getSubscriptions(),
  });

  const cancelMutation = useMutation({
    mutationFn: cancelSubscription,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["subscriptions"] }),
  });

  const plans = plansQuery.data?.results ?? [];
  const subscriptions = subscriptionsQuery.data?.results ?? [];

  return (
    <div className="flex flex-col gap-8 p-6">
      <div className="flex items-center justify-between">
        <h1 className="font-heading text-2xl font-semibold">{t("subscriptions.plansTitle")}</h1>
        <Button size="sm" onClick={() => setPlanDialog("create")}>
          {t("subscriptions.newPlan")}
        </Button>
      </div>

      {plansQuery.isLoading && (
        <p className="text-sm text-muted-foreground">{t("subscriptions.loadingPlans")}</p>
      )}
      {plansQuery.isError && (
        <p role="alert" className="text-sm text-destructive">
          {t("subscriptions.errorPlans")}
        </p>
      )}

      {!plansQuery.isLoading && !plansQuery.isError && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t("subscriptions.planTable.code")}</TableHead>
              <TableHead>{t("subscriptions.planTable.name")}</TableHead>
              <TableHead>{t("subscriptions.planTable.monthlyPrice")}</TableHead>
              <TableHead>{t("subscriptions.planTable.maxEmployees")}</TableHead>
              <TableHead>{t("subscriptions.planTable.maxBranches")}</TableHead>
              <TableHead>{t("subscriptions.planTable.gracePeriod")}</TableHead>
              <TableHead>{t("subscriptions.planTable.active")}</TableHead>
              <TableHead>{t("subscriptions.planTable.actions")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {plans.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} className="text-center text-muted-foreground">
                  {t("subscriptions.noPlans")}
                </TableCell>
              </TableRow>
            )}
            {plans.map((plan) => (
              <TableRow key={plan.id}>
                <TableCell>{plan.code}</TableCell>
                <TableCell>{plan.name}</TableCell>
                <TableCell>{plan.monthly_price}</TableCell>
                <TableCell>{plan.max_employees}</TableCell>
                <TableCell>{plan.max_branches}</TableCell>
                <TableCell>
                  {t("subscriptions.planTable.gracePeriodDays", { count: plan.grace_period_days })}
                </TableCell>
                <TableCell>
                  <Badge variant={plan.is_active ? "default" : "secondary"}>
                    {plan.is_active
                      ? t("subscriptions.planTable.statusActive")
                      : t("subscriptions.planTable.statusInactive")}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Button size="sm" variant="outline" onClick={() => setPlanDialog(plan)}>
                    {t("common.edit")}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <div className="flex items-center justify-between">
        <h2 className="font-heading text-xl font-semibold">{t("subscriptions.subscriptionsHeading")}</h2>
        <Button size="sm" onClick={() => setIsAssignOpen(true)} disabled={plans.length === 0}>
          {t("subscriptions.assignSubscription")}
        </Button>
      </div>

      {subscriptionsQuery.isLoading && (
        <p className="text-sm text-muted-foreground">{t("subscriptions.loadingSubscriptions")}</p>
      )}
      {subscriptionsQuery.isError && (
        <p role="alert" className="text-sm text-destructive">
          {t("subscriptions.errorSubscriptions")}
        </p>
      )}

      {!subscriptionsQuery.isLoading && !subscriptionsQuery.isError && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t("subscriptions.subscriptionTable.organization")}</TableHead>
              <TableHead>{t("subscriptions.subscriptionTable.plan")}</TableHead>
              <TableHead>{t("subscriptions.subscriptionTable.status")}</TableHead>
              <TableHead>{t("subscriptions.subscriptionTable.start")}</TableHead>
              <TableHead>{t("subscriptions.subscriptionTable.expiry")}</TableHead>
              <TableHead>{t("subscriptions.subscriptionTable.actions")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {subscriptions.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground">
                  {t("subscriptions.noSubscriptions")}
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
                <TableCell>{subscription.start_date}</TableCell>
                <TableCell>{subscription.expiry_date}</TableCell>
                <TableCell>
                  {subscription.status !== "CANCELLED" && (
                    <Button
                      size="sm"
                      variant="destructive"
                      disabled={cancelMutation.isPending}
                      onClick={() => cancelMutation.mutate(subscription.id)}
                    >
                      {t("subscriptions.cancel")}
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <PlanDialog
        planDialog={planDialog}
        onOpenChange={(open) => !open && setPlanDialog(null)}
        onSaved={() => {
          queryClient.invalidateQueries({ queryKey: ["subscription-plans"] });
          setPlanDialog(null);
        }}
      />

      <AssignSubscriptionDialog
        plans={plans}
        open={isAssignOpen}
        onOpenChange={setIsAssignOpen}
        onAssigned={() => {
          queryClient.invalidateQueries({ queryKey: ["subscriptions"] });
          setIsAssignOpen(false);
        }}
      />
    </div>
  );
}

function PlanDialog({ planDialog, onOpenChange, onSaved }) {
  const { t } = useTranslation();
  const isEditing = planDialog && planDialog !== "create";
  const [form, setForm] = useState(() => emptyPlanForm());
  const [error, setError] = useState(null);

  // Re-seed the form whenever a different plan (or "create") is opened.
  const dialogKey = isEditing ? planDialog.id : planDialog === "create" ? "create" : "closed";
  const [lastKey, setLastKey] = useState(dialogKey);
  if (dialogKey !== lastKey) {
    setLastKey(dialogKey);
    setForm(isEditing ? planToForm(planDialog) : emptyPlanForm());
    setError(null);
  }

  const mutation = useMutation({
    mutationFn: () =>
      isEditing
        ? updatePlan(planDialog.id, {
            name: form.name,
            monthly_price: form.monthly_price,
            max_employees: Number(form.max_employees),
            max_branches: Number(form.max_branches),
            grace_period_days: Number(form.grace_period_days),
            is_active: form.is_active,
          })
        : createPlan({
            code: form.code,
            name: form.name,
            monthly_price: form.monthly_price,
            max_employees: Number(form.max_employees),
            max_branches: Number(form.max_branches),
            grace_period_days: Number(form.grace_period_days),
          }),
    onSuccess: onSaved,
    onError: (err) => setError(formatApiError(err, t("subscriptions.planDialog.genericError"))),
  });

  return (
    <Dialog open={Boolean(planDialog)} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {isEditing ? t("subscriptions.planDialog.editTitle") : t("subscriptions.planDialog.newTitle")}
          </DialogTitle>
          <DialogDescription>
            {isEditing
              ? t("subscriptions.planDialog.editingDescription", { code: planDialog.code })
              : t("subscriptions.planDialog.createDescription")}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3">
          {!isEditing && (
            <Field label={t("subscriptions.planDialog.codeLabel")}>
              <Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
            </Field>
          )}
          <Field label={t("subscriptions.planDialog.nameLabel")}>
            <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </Field>
          <Field label={t("subscriptions.planDialog.monthlyPriceLabel")}>
            <Input
              type="number"
              step="0.01"
              value={form.monthly_price}
              onChange={(e) => setForm({ ...form, monthly_price: e.target.value })}
            />
          </Field>
          <Field label={t("subscriptions.planDialog.maxEmployeesLabel")}>
            <Input
              type="number"
              value={form.max_employees}
              onChange={(e) => setForm({ ...form, max_employees: e.target.value })}
            />
          </Field>
          <Field label={t("subscriptions.planDialog.maxBranchesLabel")}>
            <Input
              type="number"
              value={form.max_branches}
              onChange={(e) => setForm({ ...form, max_branches: e.target.value })}
            />
          </Field>
          <Field label={t("subscriptions.planDialog.gracePeriodLabel")}>
            <Input
              type="number"
              value={form.grace_period_days}
              onChange={(e) => setForm({ ...form, grace_period_days: e.target.value })}
            />
          </Field>
          {isEditing && (
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
              />
              {t("subscriptions.planDialog.activeLabel")}
            </label>
          )}
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button disabled={mutation.isPending} onClick={() => mutation.mutate()}>
            {mutation.isPending ? t("common.saving") : t("common.save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function emptyPlanForm() {
  return {
    code: "",
    name: "",
    monthly_price: "",
    max_employees: "",
    max_branches: "",
    grace_period_days: "7",
    is_active: true,
  };
}

function planToForm(plan) {
  return {
    code: plan.code,
    name: plan.name,
    monthly_price: String(plan.monthly_price),
    max_employees: String(plan.max_employees),
    max_branches: String(plan.max_branches),
    grace_period_days: String(plan.grace_period_days),
    is_active: plan.is_active,
  };
}

function AssignSubscriptionDialog({ plans, open, onOpenChange, onAssigned }) {
  const { t } = useTranslation();
  const [organizationId, setOrganizationId] = useState("");
  const [planId, setPlanId] = useState("");
  const [startDate, setStartDate] = useState("");
  const [expiryDate, setExpiryDate] = useState("");
  const [error, setError] = useState(null);

  const organizationsQuery = useQuery({
    queryKey: ["organizations", "picker"],
    queryFn: () => getOrganizations(),
    enabled: open,
  });
  const organizations = organizationsQuery.data?.results ?? [];

  const mutation = useMutation({
    mutationFn: () =>
      assignSubscription({
        organization: organizationId,
        plan: planId,
        start_date: startDate,
        expiry_date: expiryDate,
      }),
    onSuccess: () => {
      setOrganizationId("");
      setPlanId("");
      setStartDate("");
      setExpiryDate("");
      setError(null);
      onAssigned();
    },
    onError: (err) => setError(formatApiError(err, t("subscriptions.assignDialog.genericError"))),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("subscriptions.assignDialog.title")}</DialogTitle>
          <DialogDescription>{t("subscriptions.assignDialog.description")}</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3">
          <Field label={t("subscriptions.assignDialog.organizationLabel")}>
            <select
              className={selectClassName}
              value={organizationId}
              onChange={(e) => setOrganizationId(e.target.value)}
            >
              <option value="">{t("subscriptions.assignDialog.organizationPlaceholder")}</option>
              {organizations.map((org) => (
                <option key={org.id} value={org.id}>
                  {org.name} ({org.code})
                </option>
              ))}
            </select>
          </Field>
          <Field label={t("subscriptions.assignDialog.planLabel")}>
            <select
              className={selectClassName}
              value={planId}
              onChange={(e) => setPlanId(e.target.value)}
            >
              <option value="">{t("subscriptions.assignDialog.planPlaceholder")}</option>
              {plans.map((plan) => (
                <option key={plan.id} value={plan.id}>
                  {plan.name} ({plan.code})
                </option>
              ))}
            </select>
          </Field>
          <Field label={t("subscriptions.assignDialog.startDateLabel")}>
            <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </Field>
          <Field label={t("subscriptions.assignDialog.expiryDateLabel")}>
            <Input type="date" value={expiryDate} onChange={(e) => setExpiryDate(e.target.value)} />
          </Field>
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button
            disabled={
              !organizationId || !planId || !startDate || !expiryDate || mutation.isPending
            }
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending
              ? t("subscriptions.assignDialog.assigning")
              : t("subscriptions.assignDialog.assign")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Field({ label, children }) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      {cloneElement(children, { id })}
    </div>
  );
}
