"use client";

import React, { useState, useEffect } from "react";
import { Check, Moon, Monitor, Sun, User as UserIcon, Lock, Save } from "lucide-react";
import { useTheme } from "@/components/theme/theme-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Notice } from "@/components/ui/notice";
import { useToast } from "@/components/ui/toast";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { useMeQuery, useUpdateMeMutation } from "@/store/api/repolensApi";
import { setUser } from "@/store/slices/authSlice";
import {
  setDependencyDepth,
  setIncludeChangedFilesInImpact,
  setIncludeExplanations,
} from "@/store/slices/appPreferencesSlice";

const themeOptions = [
  { icon: Monitor, label: "System", value: "system" as const },
  { icon: Sun, label: "Light", value: "light" as const },
  { icon: Moon, label: "Dark", value: "dark" as const },
];

export default function SettingsPage() {
  const { mode, setMode } = useTheme();
  const dispatch = useAppDispatch();
  const preferences = useAppSelector((state) => state.appPreferences);
  const authUser = useAppSelector((state) => state.auth.user);
  const { notify } = useToast();

  const { data: meData, isLoading: isLoadingMe } = useMeQuery();
  const [updateMe, { isLoading: isUpdating }] = useUpdateMeMutation();

  const currentUser = authUser || meData;

  const [fullName, setFullName] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profileSuccess, setProfileSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (currentUser?.full_name) {
      setFullName(currentUser.full_name);
    }
  }, [currentUser?.full_name]);

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setProfileError(null);
    setProfileSuccess(null);

    if (!fullName.trim()) {
      setProfileError("Full Name cannot be empty.");
      return;
    }

    if (newPassword && newPassword.length < 8) {
      setProfileError("New password must be at least 8 characters long.");
      return;
    }

    if (newPassword && newPassword !== confirmPassword) {
      setProfileError("Passwords do not match. Please check your entries.");
      return;
    }

    try {
      const updatedUser = await updateMe({
        full_name: fullName.trim() ? fullName : undefined,
        password: newPassword || undefined,
      }).unwrap();

      dispatch(setUser(updatedUser));
      setNewPassword("");
      setConfirmPassword("");
      setProfileSuccess("Profile updated successfully!");

      notify({
        title: "Profile Updated",
        description: "Your user settings have been updated successfully.",
      });
    } catch (err: unknown) {
      console.error("Failed to update profile:", err);
      const apiErr = err as { data?: { detail?: string | Record<string, unknown> } };
      const detail = apiErr?.data?.detail || "Failed to update profile. Please try again.";
      setProfileError(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="border-b border-border pb-6">
        <Badge tone="info">Settings</Badge>
        <h1 className="mt-3 text-3xl font-semibold md:text-4xl">Settings</h1>
      </div>

      <div className="max-w-2xl space-y-6">
        {/* Profile Settings Card */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <UserIcon className="size-4 text-primary" />
              <h2 className="text-sm font-semibold">User Profile & Account</h2>
            </div>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleUpdateProfile} className="space-y-4">
              {profileError && (
                <Notice tone="danger" className="text-xs">
                  {profileError}
                </Notice>
              )}

              {profileSuccess && (
                <Notice tone="success" className="text-xs">
                  {profileSuccess}
                </Notice>
              )}

              <div>
                <label className="block text-xs font-medium text-muted mb-1.5" htmlFor="profile-email">
                  Email Address
                </label>
                <Input
                  id="profile-email"
                  type="email"
                  value={currentUser?.email || ""}
                  disabled
                  className="bg-canvas/50 text-muted cursor-not-allowed"
                />
                <p className="mt-1 text-[11px] text-muted">Email address cannot be changed.</p>
              </div>

              <div>
                <label className="block text-xs font-medium text-muted mb-1.5" htmlFor="profile-fullname">
                  Full Name
                </label>
                <Input
                  id="profile-fullname"
                  type="text"
                  placeholder="Your Name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  disabled={isLoadingMe || isUpdating}
                />
              </div>

              <div className="border-t border-border/60 pt-4 mt-4 space-y-4">
                <div className="flex items-center gap-2 text-xs font-medium text-foreground">
                  <Lock className="size-3.5 text-muted" />
                  <span>Change Password (optional)</span>
                </div>

                <div>
                  <label className="block text-xs font-medium text-muted mb-1.5" htmlFor="profile-new-password">
                    New Password
                  </label>
                  <Input
                    id="profile-new-password"
                    type="password"
                    placeholder="Leave blank to keep current password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    disabled={isLoadingMe || isUpdating}
                    minLength={8}
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-muted mb-1.5" htmlFor="profile-confirm-password">
                    Confirm New Password
                  </label>
                  <Input
                    id="profile-confirm-password"
                    type="password"
                    placeholder="Confirm new password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    disabled={isLoadingMe || isUpdating}
                    minLength={8}
                  />
                </div>
              </div>

              <div className="pt-2">
                <Button
                  type="submit"
                  variant="primary"
                  className="w-full sm:w-auto flex items-center justify-center gap-2"
                  disabled={isLoadingMe || isUpdating}
                >
                  <Save className="size-4" />
                  <span>{isUpdating ? "Saving Changes..." : "Save Profile Settings"}</span>
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Theme Settings Card */}
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold">Theme</h2>
          </CardHeader>
          <CardContent>
            <div className="grid gap-2 sm:grid-cols-3">
              {themeOptions.map((option) => {
                const Icon = option.icon;
                const selected = mode === option.value;

                return (
                  <Button
                    aria-pressed={selected}
                    className="justify-between"
                    key={option.value}
                    onClick={() => setMode(option.value)}
                    type="button"
                    variant={selected ? "secondary" : "ghost"}
                  >
                    <span className="inline-flex items-center gap-2">
                      <Icon aria-hidden="true" className="size-4" />
                      {option.label}
                    </span>
                    {selected ? (
                      <Check aria-hidden="true" className="size-4 text-primary" />
                    ) : null}
                  </Button>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Analysis & Impact Preferences Card */}
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold">Analysis & Impact Preferences</h2>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-2">
              <label
                className="block text-sm font-medium"
                htmlFor="settings-dependency-depth"
              >
                Default Max Dependency Depth
              </label>
              <p className="text-xs text-muted">
                Maximum graph depth for dependency traversal when analyzing change impact.
              </p>
              <Input
                className="max-w-[120px]"
                id="settings-dependency-depth"
                max={10}
                min={1}
                onChange={(event) =>
                  dispatch(setDependencyDepth(Math.max(1, Number(event.target.value))))
                }
                type="number"
                value={preferences.dependencyDepth}
              />
            </div>

            <div className="space-y-3 pt-2">
              <label className="flex items-start gap-3 text-sm">
                <input
                  checked={preferences.includeChangedFilesInImpact}
                  className="mt-1 rounded border-border text-primary focus:ring-primary"
                  onChange={(event) =>
                    dispatch(setIncludeChangedFilesInImpact(event.target.checked))
                  }
                  type="checkbox"
                />
                <div>
                  <span className="font-medium text-foreground">
                    Include changed files in predictions
                  </span>
                  <p className="text-xs text-muted">
                    When enabled, the changed files themselves will be included alongside predicted impact files.
                  </p>
                </div>
              </label>

              <label className="flex items-start gap-3 text-sm">
                <input
                  checked={preferences.includeExplanations}
                  className="mt-1 rounded border-border text-primary focus:ring-primary"
                  onChange={(event) =>
                    dispatch(setIncludeExplanations(event.target.checked))
                  }
                  type="checkbox"
                />
                <div>
                  <span className="font-medium text-foreground">
                    Generate LLM analysis explanations
                  </span>
                  <p className="text-xs text-muted">
                    Request evidence-based explanation summaries alongside impact analysis runs.
                  </p>
                </div>
              </label>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
