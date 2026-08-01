"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAppDispatch } from "@/store/hooks";
import { useSignupMutation, useLazyMeQuery } from "@/store/api/repolensApi";
import { setCredentials } from "@/store/slices/authSlice";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Notice } from "@/components/ui/notice";
import { Logo } from "@/components/app/logo";
import { PasswordStrengthIndicator, isPasswordValid } from "@/components/auth/password-strength";

export default function SignupPage() {
  const router = useRouter();
  const dispatch = useAppDispatch();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [signup, { isLoading: isSigningUp }] = useSignupMutation();
  const [triggerMe, { isLoading: isFetchingMe }] = useLazyMeQuery();

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    const trimmedName = name.trim();
    const trimmedEmail = email.trim();

    if (!trimmedName || !trimmedEmail || !password || !confirmPassword) {
      setErrorMsg("Please fill in all fields.");
      return;
    }

    if (!isPasswordValid(password)) {
      setErrorMsg("Password must meet all complexity requirements.");
      return;
    }

    if (password !== confirmPassword) {
      setErrorMsg("Passwords do not match.");
      return;
    }

    try {
      const tokenRes = await signup({
        email: trimmedEmail,
        password,
        full_name: trimmedName,
      }).unwrap();

      dispatch(
        setCredentials({
          accessToken: tokenRes.access_token,
        })
      );

      const userRes = await triggerMe().unwrap();

      dispatch(
        setCredentials({
          accessToken: tokenRes.access_token,
          user: {
            id: userRes.id,
            email: userRes.email,
            full_name: userRes.full_name,
          },
        })
      );

      document.cookie = "repolens_logged_in=true; path=/; max-age=31536000; SameSite=Lax";
      router.push("/repositories");
    } catch (err: unknown) {
      console.error("Signup failed:", err);
      const apiErr = err as { data?: { detail?: string | Array<{ msg?: string }> | Record<string, unknown> } };
      const rawDetail = apiErr?.data?.detail;
      let msg = "Registration failed. Please try again.";
      if (typeof rawDetail === "string") {
        msg = rawDetail;
      } else if (Array.isArray(rawDetail)) {
        msg = rawDetail.map((d) => (typeof d === "string" ? d : d.msg || JSON.stringify(d))).join(", ");
      } else if (rawDetail && typeof rawDetail === "object") {
        msg = JSON.stringify(rawDetail);
      }
      setErrorMsg(msg);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-4xl grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Left Bento: Editorial/Branding Card */}
        <div className="flex flex-col justify-between rounded-lg border border-border bg-panel p-8 text-foreground min-h-[320px] md:min-h-[400px]">
          <div>
            <Logo />
            <p className="mt-8 text-sm leading-6 text-muted max-w-sm">
              Create an account to start tracking structural dependencies, predicting impact changes, and running test suite analysis on your codebases.
            </p>
          </div>
          
          <div className="mt-8 pt-6 border-t border-border/60">
            <h3 className="font-mono text-xs uppercase tracking-[0.12em] text-muted">Repository Intelligence</h3>
            <p className="mt-2 text-xs leading-5 text-muted">
              Automated codebase indexer, architecture visualizer, impact risk scorer, and semantic analysis engine.
            </p>
          </div>
        </div>

        {/* Right Bento: Form Card */}
        <div className="flex flex-col justify-between rounded-lg border border-border bg-panel p-8">
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-foreground">Create Account</h2>
            <p className="mt-1 text-xs text-muted">Get started by creating your RepoLens profile</p>

            <form onSubmit={handleSignup} className="mt-6 space-y-4">
              {errorMsg && (
                <Notice tone="danger" className="text-xs">
                  {errorMsg}
                </Notice>
              )}

              <div>
                <label className="block text-xs font-medium text-muted mb-1.5" htmlFor="name">
                  Full Name
                </label>
                <Input
                  id="name"
                  type="text"
                  placeholder="John Doe"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  disabled={isSigningUp || isFetchingMe}
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-muted mb-1.5" htmlFor="email">
                  Email Address
                </label>
                <Input
                  id="email"
                  type="email"
                  placeholder="name@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isSigningUp || isFetchingMe}
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-muted mb-1.5" htmlFor="password">
                  Password
                </label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isSigningUp || isFetchingMe}
                  required
                />
                <PasswordStrengthIndicator password={password} />
              </div>

              <div>
                <label className="block text-xs font-medium text-muted mb-1.5" htmlFor="confirmPassword">
                  Confirm Password
                </label>
                <Input
                  id="confirmPassword"
                  type="password"
                  placeholder="••••••••"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  disabled={isSigningUp || isFetchingMe}
                  required
                />
              </div>

              <Button
                type="submit"
                className="w-full"
                variant="primary"
                disabled={isSigningUp || isFetchingMe}
              >
                {isSigningUp || isFetchingMe ? "Creating account..." : "Sign Up"}
              </Button>
            </form>
          </div>

          <div className="mt-8 text-center text-xs text-muted">
            Already have an account?{" "}
            <Link href="/login" className="underline hover:text-foreground">
              Sign in
            </Link>
          </div>
        </div>

      </div>
    </div>
  );
}
