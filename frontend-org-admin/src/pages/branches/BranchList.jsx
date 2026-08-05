import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  captureBranchLocation,
  createBranch,
  deleteBranch,
  getBranches,
  updateBranch,
} from "@/api/endpoints/branches";
import { useBrowserLocation } from "@/hooks/useBrowserLocation";
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

export default function BranchList() {
  const { t } = useTranslation();
  const [dialogTarget, setDialogTarget] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [actionError, setActionError] = useState(null);
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["branches"],
    queryFn: () => getBranches(),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteBranch,
    onSuccess: () => {
      setActionError(null);
      queryClient.invalidateQueries({ queryKey: ["branches"] });
      setDeleteTarget(null);
    },
    onError: (err) => setActionError(formatApiError(err, t("branches.deleteError"))),
  });

  const branches = data?.results ?? [];

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="font-heading text-2xl font-semibold">{t("nav.branches")}</h1>
        <Button size="sm" onClick={() => setDialogTarget("create")}>
          {t("branches.new")}
        </Button>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">{t("branches.loading")}</p>}
      {isError && (
        <p role="alert" className="text-sm text-destructive">
          {t("branches.error")}
        </p>
      )}
      {actionError && (
        <p role="alert" className="text-sm text-destructive">
          {actionError}
        </p>
      )}

      {!isLoading && !isError && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t("branches.table.name")}</TableHead>
              <TableHead>{t("branches.table.address")}</TableHead>
              <TableHead>{t("branches.table.radius")}</TableHead>
              <TableHead>{t("branches.table.status")}</TableHead>
              <TableHead>{t("branches.table.actions")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {branches.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">
                  {t("branches.noResults")}
                </TableCell>
              </TableRow>
            )}
            {branches.map((branch) => (
              <TableRow key={branch.id}>
                <TableCell>{branch.name}</TableCell>
                <TableCell>{branch.address}</TableCell>
                <TableCell>{t("branches.metersValue", { value: branch.radius_meters })}</TableCell>
                <TableCell>
                  <Badge variant={branch.is_active ? "default" : "secondary"}>
                    {branch.is_active ? t("branches.active") : t("branches.inactive")}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" onClick={() => setDialogTarget(branch)}>
                      {t("common.edit")}
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      disabled={deleteMutation.isPending}
                      onClick={() => setDeleteTarget(branch)}
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

      <BranchDialog
        target={dialogTarget}
        onOpenChange={(open) => !open && setDialogTarget(null)}
        onSaved={() => {
          queryClient.invalidateQueries({ queryKey: ["branches"] });
          setDialogTarget(null);
        }}
      />

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title={t("branches.confirmDeleteTitle")}
        description={t("branches.confirmDelete", { name: deleteTarget?.name })}
        confirmLabel={t("common.delete")}
        isPending={deleteMutation.isPending}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => deleteMutation.mutate(deleteTarget.id)}
      />
    </div>
  );
}

function BranchDialog({ target, onOpenChange, onSaved }) {
  const { t } = useTranslation();
  const isEditing = target && target !== "create";
  const { capture, isLocating } = useBrowserLocation();

  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [radiusMeters, setRadiusMeters] = useState("100");
  const [accuracyLimit, setAccuracyLimit] = useState("50");
  const [isActive, setIsActive] = useState(true);
  const [location, setLocation] = useState(null); // { latitude, longitude, gps_accuracy }
  const [error, setError] = useState(null);

  const dialogKey = isEditing ? target.id : target === "create" ? "create" : "closed";
  const [lastKey, setLastKey] = useState(dialogKey);
  if (dialogKey !== lastKey) {
    setLastKey(dialogKey);
    setName(isEditing ? target.name : "");
    setAddress(isEditing ? target.address : "");
    setRadiusMeters(isEditing ? String(target.radius_meters) : "100");
    setAccuracyLimit(isEditing ? String(target.gps_accuracy_limit_meters) : "50");
    setIsActive(isEditing ? target.is_active : true);
    setLocation(null);
    setError(null);
  }

  async function handleCapture() {
    setError(null);
    try {
      const captured = await capture();
      // Same 50 m ceiling the backend enforces (apps.locations.serializers
      // ._GpsAccuracyMixin) — checked here too so a desktop browser's
      // imprecise WiFi/IP-based fallback location is caught immediately,
      // before a round trip, with a message that explains why.
      if (captured.gps_accuracy > 50) {
        setError(
          t("branches.poorAccuracyError", { meters: Math.round(captured.gps_accuracy) })
        );
        return;
      }
      setLocation(captured);
      if (isEditing) {
        await captureBranchLocation(target.id, captured);
      }
    } catch (err) {
      setError(err.message || t("branches.locationError"));
    }
  }

  const mutation = useMutation({
    mutationFn: () => {
      if (isEditing) {
        return updateBranch(target.id, {
          name,
          address,
          radius_meters: Number(radiusMeters),
          gps_accuracy_limit_meters: Number(accuracyLimit),
          is_active: isActive,
        });
      }
      return createBranch({
        name,
        address,
        radius_meters: Number(radiusMeters),
        gps_accuracy_limit_meters: Number(accuracyLimit),
        latitude: location.latitude,
        longitude: location.longitude,
        gps_accuracy: location.gps_accuracy,
      });
    },
    onSuccess: onSaved,
    onError: (err) => setError(formatApiError(err, t("branches.saveError"))),
  });

  const canSubmit = isEditing ? Boolean(name.trim()) : Boolean(name.trim() && location);

  return (
    <Dialog open={Boolean(target)} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEditing ? t("branches.editTitle") : t("branches.newTitle")}</DialogTitle>
          <DialogDescription>
            {isEditing ? t("branches.editDescription") : t("branches.newDescription")}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="branch-name">{t("branches.table.name")}</Label>
            <Input id="branch-name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="branch-address">{t("branches.table.address")}</Label>
            <Input id="branch-address" value={address} onChange={(e) => setAddress(e.target.value)} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="branch-radius">{t("branches.radiusLabel")}</Label>
            <Input
              id="branch-radius"
              type="number"
              value={radiusMeters}
              onChange={(e) => setRadiusMeters(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="branch-accuracy">{t("branches.accuracyLabel")}</Label>
            <Input
              id="branch-accuracy"
              type="number"
              value={accuracyLimit}
              onChange={(e) => setAccuracyLimit(e.target.value)}
            />
          </div>
          {isEditing && (
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
              {t("branches.active")}
            </label>
          )}

          <div className="rounded-lg border px-3 py-2">
            <p className="text-sm text-muted-foreground">
              {isEditing
                ? t("branches.currentLocation", {
                    lat: Number(target.latitude).toFixed(5),
                    lng: Number(target.longitude).toFixed(5),
                  })
                : location
                  ? t("branches.currentLocation", {
                      lat: location.latitude.toFixed(5),
                      lng: location.longitude.toFixed(5),
                    })
                  : t("branches.noLocationYet")}
            </p>
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="mt-2"
              disabled={isLocating}
              onClick={handleCapture}
            >
              {isLocating
                ? t("branches.locating")
                : isEditing
                  ? t("branches.updateLocation")
                  : t("branches.captureLocation")}
            </Button>
          </div>

          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button disabled={!canSubmit || mutation.isPending} onClick={() => mutation.mutate()}>
            {mutation.isPending ? t("common.saving") : t("common.save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
