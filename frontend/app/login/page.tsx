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
                <svg className="h-4 w-4" viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                  />
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
