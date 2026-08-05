import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  createShift,
  deleteShift,
  getAttendanceRule,
  getShifts,
  updateAttendanceRule,
  updateShift,
} from "@/api/endpoints/attendance";
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

const DAY_INDICES = [0, 1, 2, 3, 4, 5, 6];

export default function Settings() {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col gap-8 p-6">
      <h1 className="font-heading text-2xl font-semibold">{t("settings.title")}</h1>
      <ShiftsSection />
      <AttendanceRuleSection />
    </div>
  );
}

function ShiftsSection() {
  const { t } = useTranslation();
  const [dialogTarget, setDialogTarget] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({ queryKey: ["shifts"], queryFn: () => getShifts() });
  const deleteMutation = useMutation({
    mutationFn: deleteShift,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["shifts"] });
      setDeleteTarget(null);
    },
  });

  const shifts = data?.results ?? [];

  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="font-heading text-xl font-semibold">{t("settings.shiftsHeading")}</h2>
        <Button size="sm" onClick={() => setDialogTarget("create")}>
          {t("settings.newShift")}
        </Button>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">{t("settings.loadingShifts")}</p>}
      {isError && (
        <p role="alert" className="text-sm text-destructive">
          {t("settings.errorShifts")}
        </p>
      )}

      {!isLoading && !isError && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t("settings.shiftTable.name")}</TableHead>
              <TableHead>{t("settings.shiftTable.start")}</TableHead>
              <TableHead>{t("settings.shiftTable.end")}</TableHead>
              <TableHead>{t("settings.shiftTable.crossesMidnight")}</TableHead>
              <TableHead>{t("settings.shiftTable.actions")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {shifts.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">
                  {t("settings.noShifts")}
                </TableCell>
              </TableRow>
            )}
            {shifts.map((shift) => (
              <TableRow key={shift.id}>
                <TableCell>{shift.name}</TableCell>
                <TableCell>{shift.start_time}</TableCell>
                <TableCell>{shift.end_time}</TableCell>
                <TableCell>{shift.crosses_midnight ? "✓" : "—"}</TableCell>
                <TableCell>
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" onClick={() => setDialogTarget(shift)}>
                      {t("common.edit")}
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      disabled={deleteMutation.isPending}
                      onClick={() => setDeleteTarget(shift)}
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
          {deleteMutation.error?.message || t("settings.deleteShiftError")}
        </p>
      )}

      <ShiftDialog
        target={dialogTarget}
        onOpenChange={(open) => !open && setDialogTarget(null)}
        onSaved={() => {
          queryClient.invalidateQueries({ queryKey: ["shifts"] });
          setDialogTarget(null);
        }}
      />

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title={t("settings.confirmDeleteShiftTitle")}
        description={t("settings.confirmDeleteShift", { name: deleteTarget?.name })}
        confirmLabel={t("common.delete")}
        isPending={deleteMutation.isPending}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => deleteMutation.mutate(deleteTarget.id)}
      />
    </section>
  );
}

function ShiftDialog({ target, onOpenChange, onSaved }) {
  const { t } = useTranslation();
  const isEditing = target && target !== "create";

  const [name, setName] = useState("");
  const [startTime, setStartTime] = useState("08:00");
  const [endTime, setEndTime] = useState("17:00");
  const [crossesMidnight, setCrossesMidnight] = useState(false);
  const [error, setError] = useState(null);

  const dialogKey = isEditing ? target.id : target === "create" ? "create" : "closed";
  const [lastKey, setLastKey] = useState(dialogKey);
  if (dialogKey !== lastKey) {
    setLastKey(dialogKey);
    setName(isEditing ? target.name : "");
    setStartTime(isEditing ? target.start_time.slice(0, 5) : "08:00");
    setEndTime(isEditing ? target.end_time.slice(0, 5) : "17:00");
    setCrossesMidnight(isEditing ? target.crosses_midnight : false);
    setError(null);
  }

  const mutation = useMutation({
    mutationFn: () => {
      const payload = {
        name,
        start_time: startTime,
        end_time: endTime,
        crosses_midnight: crossesMidnight,
      };
      return isEditing ? updateShift(target.id, payload) : createShift(payload);
    },
    onSuccess: onSaved,
    onError: (err) => setError(formatApiError(err, t("settings.shiftDialog.saveError"))),
  });

  return (
    <Dialog open={Boolean(target)} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {isEditing ? t("settings.shiftDialog.editTitle") : t("settings.shiftDialog.newTitle")}
          </DialogTitle>
          <DialogDescription>{t("settings.shiftsHeading")}</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="shift-name">{t("settings.shiftDialog.nameLabel")}</Label>
            <Input id="shift-name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="shift-start">{t("settings.shiftDialog.startLabel")}</Label>
            <Input
              id="shift-start"
              type="time"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="shift-end">{t("settings.shiftDialog.endLabel")}</Label>
            <Input id="shift-end" type="time" value={endTime} onChange={(e) => setEndTime(e.target.value)} />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={crossesMidnight}
              onChange={(e) => setCrossesMidnight(e.target.checked)}
            />
            {t("settings.shiftDialog.crossesMidnightLabel")}
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

function AttendanceRuleSection() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["attendance-rule"],
    queryFn: () => getAttendanceRule(),
  });

  const [form, setForm] = useState(null);
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(false);

  if (data && !form) {
    setForm({
      working_days: data.working_days,
      late_threshold_minutes: String(data.late_threshold_minutes),
      early_departure_threshold_minutes: String(data.early_departure_threshold_minutes),
      overtime_threshold_minutes: String(data.overtime_threshold_minutes),
    });
  }

  const mutation = useMutation({
    mutationFn: () =>
      updateAttendanceRule({
        working_days: form.working_days,
        late_threshold_minutes: Number(form.late_threshold_minutes),
        early_departure_threshold_minutes: Number(form.early_departure_threshold_minutes),
        overtime_threshold_minutes: Number(form.overtime_threshold_minutes),
      }),
    onSuccess: () => {
      setSaved(true);
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["attendance-rule"] });
    },
    onError: (err) => setError(formatApiError(err, t("settings.ruleSaveError"))),
  });

  function toggleDay(day) {
    setSaved(false);
    setForm((prev) => ({
      ...prev,
      working_days: prev.working_days.includes(day)
        ? prev.working_days.filter((d) => d !== day)
        : [...prev.working_days, day].sort(),
    }));
  }

  return (
    <section className="flex flex-col gap-4">
      <div>
        <h2 className="font-heading text-xl font-semibold">{t("settings.ruleHeading")}</h2>
        <p className="text-sm text-muted-foreground">{t("settings.ruleDescription")}</p>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">{t("settings.loadingRule")}</p>}
      {isError && (
        <p role="alert" className="text-sm text-destructive">
          {t("settings.errorRule")}
        </p>
      )}

      {form && (
        <div className="flex max-w-md flex-col gap-4 rounded-xl border bg-card p-4">
          <div className="flex flex-col gap-1.5">
            <Label>{t("settings.workingDaysLabel")}</Label>
            <div className="flex flex-wrap gap-2">
              {DAY_INDICES.map((day) => (
                <Button
                  key={day}
                  type="button"
                  size="sm"
                  variant={form.working_days.includes(day) ? "secondary" : "ghost"}
                  onClick={() => toggleDay(day)}
                >
                  {t(`settings.days.${day}`)}
                </Button>
              ))}
            </div>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="rule-late">{t("settings.lateThresholdLabel")}</Label>
            <Input
              id="rule-late"
              type="number"
              value={form.late_threshold_minutes}
              onChange={(e) => {
                setSaved(false);
                setForm({ ...form, late_threshold_minutes: e.target.value });
              }}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="rule-early">{t("settings.earlyDepartureThresholdLabel")}</Label>
            <Input
              id="rule-early"
              type="number"
              value={form.early_departure_threshold_minutes}
              onChange={(e) => {
                setSaved(false);
                setForm({ ...form, early_departure_threshold_minutes: e.target.value });
              }}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="rule-overtime">{t("settings.overtimeThresholdLabel")}</Label>
            <Input
              id="rule-overtime"
              type="number"
              value={form.overtime_threshold_minutes}
              onChange={(e) => {
                setSaved(false);
                setForm({ ...form, overtime_threshold_minutes: e.target.value });
              }}
            />
          </div>

          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          {saved && <p className="text-sm text-emerald-600">{t("settings.ruleSaved")}</p>}

          <Button
            className="self-start"
            disabled={form.working_days.length === 0 || mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? t("common.saving") : t("common.save")}
          </Button>
        </div>
      )}
    </section>
  );
}
