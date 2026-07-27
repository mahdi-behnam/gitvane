"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAppDispatch } from "@/store/hooks";
import { useLoginMutation, useLazyMeQuery } from "@/store/api/repolensApi";
import { setCredentials } from "@/store/slices/authSlice";
import { apiBaseUrl } from "@/lib/api/client";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Notice } from "@/components/ui/notice";
import { Logo } from "@/components/app/logo";

export default function LoginPage() {
  const router = useRouter();
  const dispatch = useAppDispatch();
  
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [login, { isLoading: isLoggingIn }] = useLoginMutation();
  const [triggerMe, { isLoading: isFetchingMe }] = useLazyMeQuery();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!email || !password) {
      setErrorMsg("Please fill in all fields.");
      return;
    }

    try {
      const tokenRes = await login({ email, password }).unwrap();

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
      console.error("Login failed:", err);
      const apiErr = err as { data?: { detail?: string | Record<string, unknown> } };
      const detail = apiErr?.data?.detail || "Invalid email or password.";
      setErrorMsg(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
  };

  const googleLoginUrl = `${apiBaseUrl}/auth/oauth2/google`;

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-4xl grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Left Bento: Editorial/Branding Card */}
        <div className="flex flex-col justify-between rounded-lg border border-border bg-panel p-8 text-foreground min-h-[320px] md:min-h-[400px]">
          <div>
            <Logo />
            <p className="mt-8 text-sm leading-6 text-muted max-w-sm">
              RepoLens is an advanced development tool that helps you analyze, query, and understand your repository&apos;s code structures, dependencies, risks, and test recommendations.
            </p>
          </div>
          
          <div className="mt-8 pt-6 border-t border-border/60">
            <h3 className="font-mono text-xs uppercase tracking-[0.12em] text-muted">Aesthetics & Engine</h3>
            <p className="mt-2 text-xs leading-5 text-muted">
              Designed with a premium minimalist aesthetic. Features HSL layout styling, full dark mode support, and an advanced static analysis backend.
            </p>
          </div>
        </div>

        {/* Right Bento: Form Card */}
        <div className="flex flex-col justify-between rounded-lg border border-border bg-panel p-8">
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-foreground">Sign In</h2>
            <p className="mt-1 text-xs text-muted">Enter your details to access your account</p>

            <form onSubmit={handleLogin} className="mt-6 space-y-4">
              {errorMsg && (
                <Notice tone="danger" className="text-xs">
                  {errorMsg}
                </Notice>
              )}

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
                  disabled={isLoggingIn || isFetchingMe}
                  required
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-medium text-muted" htmlFor="password">
                    Password
                  </label>
                </div>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoggingIn || isFetchingMe}
                  required
                />
              </div>

              <Button
                type="submit"
                className="w-full"
                variant="primary"
                disabled={isLoggingIn || isFetchingMe}
              >
                {isLoggingIn || isFetchingMe ? "Signing in..." : "Sign In with Email"}
              </Button>
            </form>

            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center" aria-hidden="true">
                <div className="w-full border-t border-border" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-panel px-2 text-muted font-mono text-[10px]">Or continue with</span>
              </div>
            </div>

            <Button
              type="button"
              className="w-full flex items-center justify-center gap-2"
              variant="secondary"
              asChild
            >
              <a href={googleLoginUrl}>
                <svg className="h-4 w-4" aria-hidden="true" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12.24 10.285V14.4h6.887c-.648 2.41-2.519 4.113-5.113 4.113-3.41 0-6.19-2.78-6.19-6.19 0-3.41 2.78-6.19 6.19-6.19 1.493 0 2.859.53 3.93 1.41l3.02-3.02C18.9 2.05 15.82 1 12.24 1 6.033 1 12.24s5.033 11.24 11.24 11.24c5.937 0 10.963-4.227 10.963-11.24 0-.668-.063-1.34-.177-1.955H12.24z" />
                </svg>
                <span>Login with Google</span>
              </a>
            </Button>
          </div>

          <div className="mt-8 text-center text-xs text-muted">
            Don&apos;t have an account?{" "}
            <Link href="/signup" className="underline hover:text-foreground">
              Sign up
            </Link>
          </div>
        </div>

      </div>
    </div>
  );
}
