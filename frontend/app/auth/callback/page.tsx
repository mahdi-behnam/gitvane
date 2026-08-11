"use client";

import React, { useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAppDispatch } from "@/store/hooks";
import { useLazyMeQuery } from "@/store/api/gitvaneApi";
import { setCredentials } from "@/store/slices/authSlice";

function AuthCallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const dispatch = useAppDispatch();
  const [triggerMe] = useLazyMeQuery();

  useEffect(() => {
    async function handleCallback() {
      const hashParams = typeof window !== "undefined" && window.location.hash
        ? new URLSearchParams(window.location.hash.substring(1))
        : null;
      const accessToken = searchParams.get("access_token") || hashParams?.get("access_token");
      if (!accessToken) {
        router.replace("/login");
        return;
      }

      try {
        // Save token to Redux store first so that the rawBaseQuery can use it
        dispatch(setCredentials({ accessToken }));

        // Query /auth/me to get user details
        const userRes = await triggerMe().unwrap();

        // Save complete credentials
        dispatch(
          setCredentials({
            accessToken,
            user: {
              id: userRes.id,
              email: userRes.email,
              full_name: userRes.full_name,
            },
          })
        );

        // Set cookie
        document.cookie = "gitvane_logged_in=true; path=/; max-age=31536000; SameSite=Lax";

        // Redirect
        router.replace("/repositories");
      } catch (error) {
        console.error("OAuth callback error:", error);
        router.replace("/login");
      }
    }

    handleCallback();
  }, [searchParams, dispatch, triggerMe, router]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-canvas text-foreground">
      <div className="flex flex-col items-center gap-4">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        <p className="text-sm font-medium text-muted">Completing sign in...</p>
      </div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen flex-col items-center justify-center bg-canvas text-foreground">
          <div className="flex flex-col items-center gap-4">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            <p className="text-sm font-medium text-muted">Loading...</p>
          </div>
        </div>
      }
    >
      <AuthCallbackHandler />
    </Suspense>
  );
}
