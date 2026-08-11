"use client";

import React, { useState } from "react";
import Link from "next/link";
import { ArrowLeft, CheckCircle2, KeyRound, Link as LinkIcon } from "lucide-react";
import { useForgotPasswordMutation } from "@/store/api/gitvaneApi";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Notice } from "@/components/ui/notice";
import { Logo } from "@/components/app/logo";
import { useToast } from "@/components/ui/toast";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [devResetUrl, setDevResetUrl] = useState<string | null>(null);

  const [forgotPassword, { isLoading }] = useForgotPasswordMutation();
  const { notify } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);
    setDevResetUrl(null);

    if (!email) {
      setErrorMsg("Please enter your email address.");
      return;
    }

    try {
      const response = await forgotPassword({ email }).unwrap();
      
      const message = response.message || "If your email is registered, you will receive a password reset link.";
      setSuccessMsg(message);

      if (response.reset_url) {
        setDevResetUrl(response.reset_url);
        notify({
          title: "Dev Mode: Password Reset Link Generated",
          description: response.reset_url,
        });
      } else {
        notify({
          title: "Request Sent",
          description: message,
        });
      }
    } catch (err: unknown) {
      console.error("Forgot password request failed:", err);
      const apiErr = err as { data?: { detail?: string | Record<string, unknown> } };
      const detail = apiErr?.data?.detail || "An error occurred while requesting password reset. Please try again.";
      setErrorMsg(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-4xl grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Left Bento: Info / Branding Card */}
        <div className="flex flex-col justify-between rounded-lg border border-border bg-panel p-8 text-foreground min-h-[320px] md:min-h-[400px]">
          <div>
            <Logo />
            <div className="mt-8 flex items-center gap-3">
              <div className="flex size-10 items-center justify-center rounded-lg border border-border bg-canvas text-primary">
                <KeyRound className="size-5" />
              </div>
              <h2 className="text-xl font-semibold tracking-tight text-foreground">
                Password Recovery
              </h2>
            </div>
            <p className="mt-4 text-sm leading-6 text-muted max-w-sm">
              Forgot your account password? No worries. Enter your registered email address and we&apos;ll send you instructions to reset your password.
            </p>
          </div>
          
          <div className="mt-8 pt-6 border-t border-border/60">
            <h3 className="font-mono text-xs uppercase tracking-[0.12em] text-muted">Security First</h3>
            <p className="mt-2 text-xs leading-5 text-muted">
              Password reset links expire automatically for your security. Please check your inbox and spam folder for instructions.
            </p>
          </div>
        </div>

        {/* Right Bento: Form Card */}
        <div className="flex flex-col justify-between rounded-lg border border-border bg-panel p-8">
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-foreground">Reset Request</h2>
            <p className="mt-1 text-xs text-muted">Enter your email to receive a password reset link</p>

            <form onSubmit={handleSubmit} className="mt-6 space-y-4">
              {errorMsg && (
                <Notice tone="danger" className="text-xs">
                  {errorMsg}
                </Notice>
              )}

              {successMsg && (
                <Notice tone="success" className="text-xs">
                  <div className="flex items-start gap-2">
                    <CheckCircle2 className="size-4 shrink-0 text-emerald-500 mt-0.5" />
                    <div>
                      <span>{successMsg}</span>
                    </div>
                  </div>
                </Notice>
              )}

              {devResetUrl && (
                <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200 space-y-2">
                  <div className="flex items-center gap-1.5 font-medium text-amber-400">
                    <LinkIcon className="size-3.5" />
                    <span>Dev Mode Reset Link:</span>
                  </div>
                  <div className="break-all font-mono text-[11px] bg-black/40 p-2 rounded border border-amber-500/20">
                    {devResetUrl}
                  </div>
                  <div className="pt-1">
                    <Button
                      type="button"
                      variant="secondary"
                      className="text-xs h-7 px-3 w-full"
                      asChild
                    >
                      <a href={devResetUrl}>Open Reset Link</a>
                    </Button>
                  </div>
                </div>
              )}

              <div>
                <label className="block text-xs font-medium text-muted mb-1.5" htmlFor="forgot-email">
                  Email Address
                </label>
                <Input
                  id="forgot-email"
                  type="email"
                  placeholder="name@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isLoading}
                  required
                />
              </div>

              <Button
                type="submit"
                className="w-full"
                variant="primary"
                disabled={isLoading}
              >
                {isLoading ? "Sending Link..." : "Send Reset Link"}
              </Button>
            </form>
          </div>

          <div className="mt-8 text-center text-xs text-muted">
            <Link href="/login" className="inline-flex items-center gap-1.5 hover:text-foreground">
              <ArrowLeft className="size-3.5" />
              <span>Back to Sign In</span>
            </Link>
          </div>
        </div>

      </div>
    </div>
  );
}
