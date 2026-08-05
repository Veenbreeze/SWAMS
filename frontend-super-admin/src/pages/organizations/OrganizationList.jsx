import { cloneElement, useId, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  activateOrganization,
  createOrganization,
  getOrganizations,
  suspendOrganization,
  updateOrganization,
} from "@/api/endpoints/organizations";
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

const STATUS_BADGE_VARIANT = {
  TRIAL: "outline",
  ACTIVE: "default",
  SUSPENDED: "destructive",
  CANCELLED: "secondary",
};

export default function OrganizationList() {
  const { t } = useTranslation();
  const [dialogTarget, setDialogTarget] = useState(null);
  const [suspendTarget, setSuspendTarget] = useState(null);
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["organizations"],
    queryFn: () => getOrganizations(),
  });

  const suspendMutation = useMutation({
    mutationFn: suspendOrganization,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organizations"] });
      setSuspendTarget(null);
    },
  });
  const activateMutation = useMutation({
    mutationFn: activateOrganization,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["organizations"] }),
  });

  const organizations = data?.results ?? [];

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="font-heading text-2xl font-semibold">{t("nav.organizations")}</h1>
        <Button size="sm" onClick={() => setDialogTarget("create")}>
          {t("organizations.new")}
        </Button>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">{t("organizations.loading")}</p>}
      {isError && (
        <p role="alert" className="text-sm text-destructive">
          {t("organizations.error")}
        </p>
      )}

      {!isLoading && !isError && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t("organizations.table.code")}</TableHead>
              <TableHead>{t("organizations.table.name")}</TableHead>
              <TableHead>{t("organizations.table.email")}</TableHead>
              <TableHead>{t("organizations.table.status")}</TableHead>
              <TableHead>{t("organizations.table.actions")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {organizations.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">
                  {t("organizations.noResults")}
                </TableCell>
              </TableRow>
            )}
            {organizations.map((org) => (
              <TableRow key={org.id}>
                <TableCell>{org.code}</TableCell>
                <TableCell>{org.name}</TableCell>
                <TableCell>{org.email}</TableCell>
                <TableCell>
                  <Badge variant={STATUS_BADGE_VARIANT[org.status] ?? "outline"}>{org.status}</Badge>
                </TableCell>
                <TableCell>
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" onClick={() => setDialogTarget(org)}>
                      {t("common.edit")}
                    </Button>
                    {org.status === "SUSPENDED" ? (
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={activateMutation.isPending}
                        onClick={() => activateMutation.mutate(org.id)}
                      >
                        {t("organizations.activate")}
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        variant="destructive"
                        disabled={suspendMutation.isPending}
                        onClick={() => setSuspendTarget(org)}
                      >
                        {t("organizations.suspend")}
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <OrganizationDialog
        target={dialogTarget}
        onOpenChange={(open) => !open && setDialogTarget(null)}
        onSaved={() => {
          queryClient.invalidateQueries({ queryKey: ["organizations"] });
          setDialogTarget(null);
        }}
      />

      <ConfirmDialog
        open={Boolean(suspendTarget)}
        title={t("organizations.confirmSuspendTitle")}
        description={t("organizations.confirmSuspend", { name: suspendTarget?.name })}
        confirmLabel={t("organizations.suspend")}
        isPending={suspendMutation.isPending}
        onCancel={() => setSuspendTarget(null)}
        onConfirm={() => suspendMutation.mutate(suspendTarget.id)}
      />
    </div>
  );
}

function OrganizationDialog({ target, onOpenChange, onSaved }) {
  const { t } = useTranslation();
  const isEditing = target && target !== "create";

  const [form, setForm] = useState(() => emptyForm());
  const [error, setError] = useState(null);

  const dialogKey = isEditing ? target.id : target === "create" ? "create" : "closed";
  const [lastKey, setLastKey] = useState(dialogKey);
  if (dialogKey !== lastKey) {
    setLastKey(dialogKey);
    setForm(isEditing ? orgToForm(target) : emptyForm());
    setError(null);
  }

  const mutation = useMutation({
    mutationFn: () => {
      if (isEditing) {
        return updateOrganization(target.id, {
          name: form.name,
          email: form.email,
          phone: form.phone,
          address: form.address,
          logo_url: form.logo_url,
        });
      }
      return createOrganization(form);
    },
    onSuccess: () => onSaved(),
    onError: (err) => setError(formatApiError(err, t("organizations.saveError"))),
  });

  return (
    <Dialog open={Boolean(target)} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {isEditing ? t("organizations.editTitle") : t("organizations.newTitle")}
          </DialogTitle>
          <DialogDescription>
            {isEditing ? t("organizations.editDescription") : t("organizations.newDescription")}
          </DialogDescription>
        </DialogHeader>

        <div className="flex max-h-[60vh] flex-col gap-3 overflow-y-auto">
          {!isEditing && (
            <Field label={t("organizations.table.code")}>
              <Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
            </Field>
          )}
          <Field label={t("organizations.table.name")}>
            <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </Field>
          {!isEditing && (
            <Field label={t("organizations.registrationNumberLabel")}>
              <Input
                value={form.registration_number}
                onChange={(e) => setForm({ ...form, registration_number: e.target.value })}
              />
            </Field>
          )}
          <Field label={t("organizations.table.email")}>
            <Input
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </Field>
          <Field label={t("organizations.phoneLabel")}>
            <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          </Field>
          <Field label={t("organizations.addressLabel")}>
            <Input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
          </Field>
          <Field label={t("organizations.logoUrlLabel")}>
            <Input
              value={form.logo_url}
              onChange={(e) => setForm({ ...form, logo_url: e.target.value })}
            />
          </Field>
          {!isEditing && (
            <>
              <Field label={t("organizations.adminEmailLabel")}>
                <Input
                  type="email"
                  value={form.admin_email}
                  onChange={(e) => setForm({ ...form, admin_email: e.target.value })}
                />
              </Field>
              <Field label={t("organizations.adminPasswordLabel")}>
                <Input
                  type="password"
                  value={form.admin_password}
                  onChange={(e) => setForm({ ...form, admin_password: e.target.value })}
                />
              </Field>
              <p className="text-xs text-muted-foreground">
                {t("organizations.adminPasswordHint")}
              </p>
            </>
          )}

          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button
            disabled={
              !form.name.trim() ||
              !form.email.trim() ||
              (!isEditing &&
                (!form.code.trim() ||
                  !form.registration_number.trim() ||
                  !form.admin_email.trim() ||
                  form.admin_password.trim().length < 10)) ||
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
    code: "",
    name: "",
    registration_number: "",
    email: "",
    phone: "",
    address: "",
    logo_url: "",
    admin_email: "",
    admin_password: "",
  };
}

function orgToForm(org) {
  return {
    code: org.code,
    name: org.name,
    registration_number: org.registration_number,
    email: org.email,
    phone: org.phone,
    address: org.address ?? "",
    logo_url: org.logo_url ?? "",
    admin_email: "",
    admin_password: "",
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
