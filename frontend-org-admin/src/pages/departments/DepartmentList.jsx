import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  createDepartment,
  deleteDepartment,
  getDepartments,
  updateDepartment,
} from "@/api/endpoints/departments";
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

export default function DepartmentList() {
  const { t } = useTranslation();
  const [dialogTarget, setDialogTarget] = useState(null); // null | "create" | department object
  const [deleteTarget, setDeleteTarget] = useState(null); // null | department object
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["departments"],
    queryFn: () => getDepartments(),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDepartment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["departments"] });
      setDeleteTarget(null);
    },
  });

  const departments = data?.results ?? [];

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="font-heading text-2xl font-semibold">{t("nav.departments")}</h1>
        <Button size="sm" onClick={() => setDialogTarget("create")}>
          {t("departments.new")}
        </Button>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">{t("departments.loading")}</p>}
      {isError && (
        <p role="alert" className="text-sm text-destructive">
          {t("departments.error")}
        </p>
      )}

      {!isLoading && !isError && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t("departments.table.name")}</TableHead>
              <TableHead>{t("departments.table.parent")}</TableHead>
              <TableHead>{t("departments.table.actions")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {departments.length === 0 && (
              <TableRow>
                <TableCell colSpan={3} className="text-center text-muted-foreground">
                  {t("departments.noResults")}
                </TableCell>
              </TableRow>
            )}
            {departments.map((department) => (
              <TableRow key={department.id}>
                <TableCell>{department.name}</TableCell>
                <TableCell>
                  {departments.find((d) => d.id === department.parent_department)?.name ?? "—"}
                </TableCell>
                <TableCell>
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" onClick={() => setDialogTarget(department)}>
                      {t("common.edit")}
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      disabled={deleteMutation.isPending}
                      onClick={() => setDeleteTarget(department)}
                    >
                      {t("common.delete")}
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {deleteMutation.isError && (
        <p role="alert" className="text-sm text-destructive">
          {deleteMutation.error?.message || t("departments.deleteError")}
        </p>
      )}

      <DepartmentDialog
        target={dialogTarget}
        departments={departments}
        onOpenChange={(open) => !open && setDialogTarget(null)}
        onSaved={() => {
          queryClient.invalidateQueries({ queryKey: ["departments"] });
          setDialogTarget(null);
        }}
      />

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title={t("departments.confirmDeleteTitle", { name: deleteTarget?.name })}
        description={t("departments.confirmDelete", { name: deleteTarget?.name })}
        confirmLabel={t("common.delete")}
        isPending={deleteMutation.isPending}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => deleteMutation.mutate(deleteTarget.id)}
      />
    </div>
  );
}

function DepartmentDialog({ target, departments, onOpenChange, onSaved }) {
  const { t } = useTranslation();
  const isEditing = target && target !== "create";
  const [name, setName] = useState("");
  const [parentDepartment, setParentDepartment] = useState("");
  const [error, setError] = useState(null);

  const dialogKey = isEditing ? target.id : target === "create" ? "create" : "closed";
  const [lastKey, setLastKey] = useState(dialogKey);
  if (dialogKey !== lastKey) {
    setLastKey(dialogKey);
    setName(isEditing ? target.name : "");
    setParentDepartment(isEditing ? target.parent_department ?? "" : "");
    setError(null);
  }

  const mutation = useMutation({
    mutationFn: () => {
      const payload = { name, parent_department: parentDepartment || null };
      return isEditing ? updateDepartment(target.id, payload) : createDepartment(payload);
    },
    onSuccess: onSaved,
    onError: (err) => setError(formatApiError(err, t("departments.saveError"))),
  });

  return (
    <Dialog open={Boolean(target)} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEditing ? t("departments.editTitle") : t("departments.newTitle")}</DialogTitle>
          <DialogDescription>{t("departments.dialogDescription")}</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="department-name">{t("departments.table.name")}</Label>
            <Input id="department-name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="department-parent">{t("departments.table.parent")}</Label>
            <select
              id="department-parent"
              className="clay-inset h-8 w-full min-w-0 rounded-xl border border-transparent bg-transparent px-2.5 py-1 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
              value={parentDepartment}
              onChange={(e) => setParentDepartment(e.target.value)}
            >
              <option value="">{t("departments.noParent")}</option>
              {departments
                .filter((d) => !isEditing || d.id !== target.id)
                .map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
            </select>
          </div>
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
