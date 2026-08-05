import { useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  changePassword,
  requestProfilePictureUpload,
  uploadToSignedUrl,
} from "@/api/endpoints/auth";
import { useAuth } from "@/hooks/useAuth";
import { Avatar } from "@/components/ui/avatar";
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

export default function ProfileDialog({ open, onOpenChange }) {
  const { t } = useTranslation();
  const { user, updateUser } = useAuth();
  const fileInputRef = useRef(null);
  const [pictureError, setPictureError] = useState(null);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [passwordError, setPasswordError] = useState(null);
  const [passwordSuccess, setPasswordSuccess] = useState(false);

  const pictureMutation = useMutation({
    mutationFn: async (file) => {
      const { upload_url, profile_picture_url } = await requestProfilePictureUpload({
        contentType: file.type,
        fileSize: file.size,
      });
      await uploadToSignedUrl({ uploadUrl: upload_url, file, contentType: file.type });
      return profile_picture_url;
    },
    onSuccess: (profile_picture_url) => {
      setPictureError(null);
      updateUser({ profile_picture_url });
    },
    onError: (err) => setPictureError(formatApiError(err, t("profileDialog.pictureError"))),
  });

  const passwordMutation = useMutation({
    mutationFn: () => changePassword({ currentPassword, newPassword }),
    onSuccess: () => {
      setPasswordError(null);
      setPasswordSuccess(true);
      setCurrentPassword("");
      setNewPassword("");
    },
    onError: (err) => {
      setPasswordSuccess(false);
      setPasswordError(formatApiError(err, t("profileDialog.passwordError")));
    },
  });

  function handleFileChange(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (file) pictureMutation.mutate(file);
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) {
          setPasswordError(null);
          setPasswordSuccess(false);
          setCurrentPassword("");
          setNewPassword("");
        }
        onOpenChange(next);
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("profileDialog.title")}</DialogTitle>
          <DialogDescription>{user?.email}</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-5">
          <div className="flex items-center gap-3">
            <Avatar
              src={user?.profile_picture_url}
              name={user?.email}
              className="size-14 text-base"
            />
            <div className="flex flex-col gap-1">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                onChange={handleFileChange}
              />
              <Button
                size="sm"
                variant="outline"
                disabled={pictureMutation.isPending}
                onClick={() => fileInputRef.current?.click()}
              >
                {pictureMutation.isPending
                  ? t("profileDialog.uploading")
                  : t("profileDialog.changePicture")}
              </Button>
              {pictureError && (
                <p role="alert" className="text-xs text-destructive">
                  {pictureError}
                </p>
              )}
            </div>
          </div>

          <div className="flex flex-col gap-3 border-t pt-4">
            <h3 className="text-sm font-medium">{t("profileDialog.passwordSectionTitle")}</h3>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="profile-current-password">
                {t("profileDialog.currentPasswordLabel")}
              </Label>
              <Input
                id="profile-current-password"
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="profile-new-password">{t("profileDialog.newPasswordLabel")}</Label>
              <Input
                id="profile-new-password"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
              />
            </div>
            {passwordError && (
              <p role="alert" className="text-sm text-destructive">
                {passwordError}
              </p>
            )}
            {passwordSuccess && (
              <p className="text-sm text-primary">{t("profileDialog.passwordSuccess")}</p>
            )}
            <Button
              size="sm"
              disabled={
                !currentPassword.trim() || !newPassword.trim() || passwordMutation.isPending
              }
              onClick={() => passwordMutation.mutate()}
            >
              {passwordMutation.isPending
                ? t("profileDialog.changingPassword")
                : t("profileDialog.changePassword")}
            </Button>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t("common.close")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
