"use client";

import React, { useState, Suspense } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { ArrowLeft, CheckCircle2, ShieldCheck } from "lucide-react";
import { useResetPasswordMutation } from "@/store/api/repolensApi";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Notice } from "@/components/ui/notice";
import { Logo } from "@/components/app/logo";
import { useToast } from "@/components/ui/toast";

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token");

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);

  const [resetPassword, { isLoading }] = useResetPasswordMutation();
  const { notify } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!token) {
      setErrorMsg("Missing or invalid password reset token. Please request a new password reset link.");
      return;
    }

    if (!newPassword || !confirmPassword) {
      setErrorMsg("Please fill in all password fields.");
      return;
    }

    if (newPassword.length < 8) {
      setErrorMsg("Password must be at least 8 characters long.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setErrorMsg("Passwords do not match. Please verify your entries.");
      return;
    }

    try {
      const response = await resetPassword({
        token,
        new_password: newPassword,
      }).unwrap();

      setIsSuccess(true);
      notify({
        title: "Password Reset Successful",
        description: response.message || "Your password has been reset successfully.",
      });
    } catch (err: unknown) {
      console.error("Reset password failed:", err);
      const apiErr = err as { data?: { detail?: string | Record<string, unknown> } };
      const detail = apiErr?.data?.detail || "Failed to reset password. The reset link may have expired.";
      setErrorMsg(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
  };

  return (
    <div className="flex flex-col justify-between rounded-lg border border-border bg-panel p-8">
      <div>
        <h2 className="text-xl font-semibold tracking-tight text-foreground">Set New Password</h2>
        <p className="mt-1 text-xs text-muted">Create a strong new password for your account</p>

        {!token && (
          <div className="mt-6">
            <Notice tone="danger" className="text-xs">
              No reset token found in URL. Please check your reset email or request a new password reset.
            </Notice>
            <div className="mt-4">
              <Button asChild variant="secondary" className="w-full">
                <Link href="/forgot-password">Request Reset Link</Link>
              </Button>
            </div>
          </div>
        )}

        {token && isSuccess ? (
          <div className="mt-6 space-y-4">
            <Notice tone="success" className="text-xs">
              <div className="flex items-start gap-2">
                <CheckCircle2 className="size-4 shrink-0 text-emerald-500 mt-0.5" />
                <div>
                  <span className="font-semibold block">Password Updated Successfully!</span>
                  <span className="mt-1 block">You can now log in using your new credentials.</span>
                </div>
              </div>
            </Notice>
            <Button
              onClick={() => router.push("/login")}
              variant="primary"
              className="w-full mt-4"
            >
              Proceed to Sign In
            </Button>
          </div>
        ) : token ? (
          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            {errorMsg && (
              <Notice tone="danger" className="text-xs">
                {errorMsg}
              </Notice>
            )}

            <div>
              <label className="block text-xs font-medium text-muted mb-1.5" htmlFor="new-password">
                New Password
              </label>
              <Input
                id="new-password"
                type="password"
                placeholder="••••••••"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                disabled={isLoading}
                required
                minLength={8}
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-muted mb-1.5" htmlFor="confirm-password">
                Confirm New Password
              </label>
              <Input
                id="confirm-password"
                type="password"
                placeholder="••••••••"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={isLoading}
                required
                minLength={8}
              />
            </div>

            <Button
              type="submit"
              className="w-full"
              variant="primary"
              disabled={isLoading}
            >
              {isLoading ? "Updating Password..." : "Reset Password"}
            </Button>
          </form>
        ) : null}
      </div>

      <div className="mt-8 text-center text-xs text-muted">
        <Link href="/login" className="inline-flex items-center gap-1.5 hover:text-foreground">
          <ArrowLeft className="size-3.5" />
          <span>Back to Sign In</span>
        </Link>
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-4xl grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Left Bento: Info Card */}
        <div className="flex flex-col justify-between rounded-lg border border-border bg-panel p-8 text-foreground min-h-[320px] md:min-h-[400px]">
          <div>
            <Logo />
            <div className="mt-8 flex items-center gap-3">
              <div className="flex size-10 items-center justify-center rounded-lg border border-border bg-canvas text-primary">
                <ShieldCheck className="size-5" />
              </div>
              <h2 className="text-xl font-semibold tracking-tight text-foreground">
                Account Security
              </h2>
            </div>
            <p className="mt-4 text-sm leading-6 text-muted max-w-sm">
              Please enter your new password. Make sure it is at least 8 characters long and contains a mix of characters for maximum security.
            </p>
          </div>
          
          <div className="mt-8 pt-6 border-t border-border/60">
            <h3 className="font-mono text-xs uppercase tracking-[0.12em] text-muted">Token Verification</h3>
            <p className="mt-2 text-xs leading-5 text-muted">
              Once reset, all active sessions and refresh tokens associated with your account will be revoked automatically.
            </p>
          </div>
        </div>

        {/* Right Bento: Form Card wrapped in Suspense */}
        <Suspense fallback={
          <div className="flex flex-col justify-center items-center rounded-lg border border-border bg-panel p-8 min-h-[300px]">
            <p className="text-xs text-muted">Loading reset token...</p>
          </div>
        }>
          <ResetPasswordForm />
        </Suspense>

      </div>
    </div>
  );
}
