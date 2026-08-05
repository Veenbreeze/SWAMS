import { cloneElement, useId, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { getBranches } from "@/api/endpoints/branches";
import { getDepartments } from "@/api/endpoints/departments";
import { getShifts } from "@/api/endpoints/attendance";
import {
  createEmployee,
  getEmployees,
  resetEmployeePassword,
  terminateEmployee,
  updateEmployee,
} from "@/api/endpoints/employees";
import { Avatar } from "@/components/ui/avatar";
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
import ConfirmDialog from "@/components/ConfirmDialog";
import { formatApiError } from "@/lib/utils";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const selectClassName =
  "clay-inset h-8 w-full min-w-0 rounded-xl border border-transparent bg-transparent px-2.5 py-1 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

export default function EmployeeList() {
  const { t } = useTranslation();
  const [dialogTarget, setDialogTarget] = useState(null);
  const [temporaryPassword, setTemporaryPassword] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [resetTarget, setResetTarget] = useState(null);
  const [terminateTarget, setTerminateTarget] = useState(null);
  const queryClient = useQueryClient();

  const employeesQuery = useQuery({ queryKey: ["employees"], queryFn: () => getEmployees() });
  const departmentsQuery = useQuery({ queryKey: ["departments"], queryFn: () => getDepartments() });
  const branchesQuery = useQuery({ queryKey: ["branches"], queryFn: () => getBranches() });
  const shiftsQuery = useQuery({ queryKey: ["shifts"], queryFn: () => getShifts() });

  const terminateMutation = useMutation({
    mutationFn: terminateEmployee,
    onSuccess: () => {
      setActionError(null);
      setTerminateTarget(null);
      queryClient.invalidateQueries({ queryKey: ["employees"] });
    },
    onError: (err) => setActionError(formatApiError(err, t("employees.terminateError"))),
  });
  const resetPasswordMutation = useMutation({
    mutationFn: resetEmployeePassword,
    onSuccess: (data) => {
      setActionError(null);
      setResetTarget(null);
      setTemporaryPassword(data.temporary_password);
    },
    onError: (err) => setActionError(formatApiError(err, t("employees.resetPasswordError"))),
  });

  const employees = employeesQuery.data?.results ?? [];
  const departments = departmentsQuery.data?.results ?? [];
  const branches = branchesQuery.data?.results ?? [];
  const shifts = shiftsQuery.data?.results ?? [];

  function nameFor(list, id) {
    return list.find((item) => item.id === id)?.name ?? "—";
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="font-heading text-2xl font-semibold">{t("nav.employees")}</h1>
        <Button size="sm" onClick={() => setDialogTarget("create")}>
          {t("employees.new")}
        </Button>
      </div>

      {employeesQuery.isLoading && (
        <p className="text-sm text-muted-foreground">{t("employees.loading")}</p>
      )}
      {employeesQuery.isError && (
        <p role="alert" className="text-sm text-destructive">
          {t("employees.error")}
        </p>
      )}
      {actionError && (
        <p role="alert" className="text-sm text-destructive">
          {actionError}
        </p>
      )}

      {!employeesQuery.isLoading && !employeesQuery.isError && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t("employees.table.name")}</TableHead>
              <TableHead>{t("employees.table.number")}</TableHead>
              <TableHead>{t("employees.table.email")}</TableHead>
              <TableHead>{t("employees.table.role")}</TableHead>
              <TableHead>{t("employees.table.department")}</TableHead>
              <TableHead>{t("employees.table.status")}</TableHead>
              <TableHead>{t("employees.table.actions")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {employees.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-muted-foreground">
                  {t("employees.noResults")}
                </TableCell>
              </TableRow>
            )}
            {employees.map((employee) => (
              <TableRow key={employee.id}>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Avatar
                      src={employee.profile_picture_url}
                      name={`${employee.first_name} ${employee.last_name}`}
                    />
                    <span>
                      {employee.first_name} {employee.last_name}
                    </span>
                  </div>
                </TableCell>
                <TableCell>{employee.employee_number}</TableCell>
                <TableCell>{employee.email}</TableCell>
                <TableCell>{employee.role}</TableCell>
                <TableCell>{nameFor(departments, employee.department)}</TableCell>
                <TableCell>
                  <Badge variant={employee.employment_status === "ACTIVE" ? "default" : "secondary"}>
                    {employee.employment_status}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" onClick={() => setDialogTarget(employee)}>
                      {t("common.edit")}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={resetPasswordMutation.isPending}
                      onClick={() => setResetTarget(employee)}
                    >
                      {t("employees.resetPassword")}
                    </Button>
                    {employee.employment_status !== "TERMINATED" && (
                      <Button
                        size="sm"
                        variant="destructive"
                        disabled={terminateMutation.isPending}
                        onClick={() => setTerminateTarget(employee)}
                      >
                        {t("employees.terminate")}
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <EmployeeDialog
        target={dialogTarget}
        departments={departments}
        branches={branches}
        shifts={shifts}
        onOpenChange={(open) => !open && setDialogTarget(null)}
        onSaved={() => {
          queryClient.invalidateQueries({ queryKey: ["employees"] });
          setDialogTarget(null);
        }}
      />

      {/* Only for the reset-password action — the create flow shows its
          one-time password inline within EmployeeDialog itself (below)
          rather than as a second Dialog, since closing one Dialog while
          opening another in the same state update leaves Radix's overlay
          transition in a stuck, unclickable state. */}
      <Dialog open={Boolean(temporaryPassword)} onOpenChange={(open) => !open && setTemporaryPassword(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("employees.temporaryPasswordTitle")}</DialogTitle>
            <DialogDescription>{t("employees.temporaryPasswordDescription")}</DialogDescription>
          </DialogHeader>
          <div className="rounded-lg border bg-muted/50 p-3 font-mono text-sm">{temporaryPassword}</div>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={Boolean(resetTarget)}
        title={t("employees.confirmResetPasswordTitle")}
        description={t("employees.confirmResetPassword")}
        confirmLabel={t("employees.resetPassword")}
        destructive={false}
        isPending={resetPasswordMutation.isPending}
        onCancel={() => setResetTarget(null)}
        onConfirm={() => resetPasswordMutation.mutate(resetTarget.id)}
      />

      <ConfirmDialog
        open={Boolean(terminateTarget)}
        title={t("employees.confirmTerminateTitle")}
        description={t("employees.confirmTerminate", {
          name: terminateTarget ? `${terminateTarget.first_name} ${terminateTarget.last_name}` : "",
        })}
        confirmLabel={t("employees.terminate")}
        isPending={terminateMutation.isPending}
        onCancel={() => setTerminateTarget(null)}
        onConfirm={() => terminateMutation.mutate(terminateTarget.id)}
      />
    </div>
  );
}

function EmployeeDialog({ target, departments, branches, shifts, onOpenChange, onSaved }) {
  const { t } = useTranslation();
  const isEditing = target && target !== "create";

  const [form, setForm] = useState(() => emptyForm());
  const [error, setError] = useState(null);

  const dialogKey = isEditing ? target.id : target === "create" ? "create" : "closed";
  const [lastKey, setLastKey] = useState(dialogKey);
  if (dialogKey !== lastKey) {
    setLastKey(dialogKey);
    setForm(isEditing ? employeeToForm(target) : emptyForm());
    setError(null);
  }

  const mutation = useMutation({
    mutationFn: () => {
      const shared = {
        employee_number: form.employee_number,
        first_name: form.first_name,
        last_name: form.last_name,
        phone: form.phone,
        department: form.department || null,
        branch: form.branch || null,
        shift: form.shift || null,
        position: form.position,
        joining_date: form.joining_date,
      };
      if (isEditing) return updateEmployee(target.id, shared);
      return createEmployee({
        email: form.email,
        password: form.password,
        role: form.role,
        ...shared,
      });
    },
    onSuccess: () => onSaved(),
    onError: (err) => setError(formatApiError(err, t("employees.saveError"))),
  });

  return (
    <Dialog open={Boolean(target)} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEditing ? t("employees.editTitle") : t("employees.newTitle")}</DialogTitle>
          <DialogDescription>
            {isEditing ? t("employees.editDescription") : t("employees.newDescription")}
          </DialogDescription>
        </DialogHeader>

        <div className="flex max-h-[60vh] flex-col gap-3 overflow-y-auto">
          {isEditing && (
            <div className="flex items-center gap-3">
              <Avatar
                src={target.profile_picture_url}
                name={`${target.first_name} ${target.last_name}`}
                className="size-14 text-base"
              />
            </div>
          )}
          {!isEditing && (
            <>
              <Field label={t("employees.table.email")}>
                <Input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
              </Field>
              <Field label={t("employees.passwordLabel")}>
                <Input
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                />
              </Field>
              <p className="text-xs text-muted-foreground">{t("employees.passwordHint")}</p>
              <Field label={t("employees.table.role")}>
                <select
                  className={selectClassName}
                  value={form.role}
                  onChange={(e) => setForm({ ...form, role: e.target.value })}
                >
                  <option value="EMPLOYEE">{t("employees.roleEmployee")}</option>
                  <option value="MANAGER">{t("employees.roleManager")}</option>
                </select>
              </Field>
            </>
          )}
          <Field label={t("employees.numberLabel")}>
            <Input
              value={form.employee_number}
              onChange={(e) => setForm({ ...form, employee_number: e.target.value })}
            />
          </Field>
          <Field label={t("employees.firstNameLabel")}>
            <Input
              value={form.first_name}
              onChange={(e) => setForm({ ...form, first_name: e.target.value })}
            />
          </Field>
          <Field label={t("employees.lastNameLabel")}>
            <Input
              value={form.last_name}
              onChange={(e) => setForm({ ...form, last_name: e.target.value })}
            />
          </Field>
          <Field label={t("employees.phoneLabel")}>
            <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          </Field>
          <Field label={t("employees.positionLabel")}>
            <Input
              value={form.position}
              onChange={(e) => setForm({ ...form, position: e.target.value })}
            />
          </Field>
          <Field label={t("employees.joiningDateLabel")}>
            <Input
              type="date"
              value={form.joining_date}
              onChange={(e) => setForm({ ...form, joining_date: e.target.value })}
            />
          </Field>
          <Field label={t("employees.table.department")}>
            <select
              className={selectClassName}
              value={form.department}
              onChange={(e) => setForm({ ...form, department: e.target.value })}
            >
              <option value="">{t("employees.noneOption")}</option>
              {departments.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t("branches.table.name")}>
            <select
              className={selectClassName}
              value={form.branch}
              onChange={(e) => setForm({ ...form, branch: e.target.value })}
            >
              <option value="">{t("employees.noneOption")}</option>
              {branches.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t("employees.shiftLabel")}>
            <select
              className={selectClassName}
              value={form.shift}
              onChange={(e) => setForm({ ...form, shift: e.target.value })}
            >
              <option value="">{t("employees.noneOption")}</option>
              {shifts.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
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
              !form.employee_number.trim() ||
              !form.first_name.trim() ||
              !form.last_name.trim() ||
              !form.joining_date ||
              (!isEditing && (!form.email.trim() || form.password.trim().length < 10)) ||
              mutation.isPending
            }
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? t("common.saving") : t("common.save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function emptyForm() {
  return {
    email: "",
    password: "",
    role: "EMPLOYEE",
    employee_number: "",
    first_name: "",
    last_name: "",
    phone: "",
    position: "",
    joining_date: "",
    department: "",
    branch: "",
    shift: "",
  };
}

function employeeToForm(employee) {
  return {
    email: employee.email ?? "",
    password: "",
    role: employee.role ?? "EMPLOYEE",
    employee_number: employee.employee_number ?? "",
    first_name: employee.first_name ?? "",
    last_name: employee.last_name ?? "",
    phone: employee.phone ?? "",
    position: employee.position ?? "",
    joining_date: employee.joining_date ?? "",
    department: employee.department ?? "",
    branch: employee.branch ?? "",
    shift: employee.shift ?? "",
  };
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
