"use client";

import { useEffect } from "react";
import { ShieldAlert } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("App boundary error caught:", error);
  }, [error]);

  return (
    <div className="flex min-h-[50vh] items-center justify-center p-4 md:p-8">
      <Card className="w-full max-w-md">
        <CardHeader className="flex flex-col items-center border-b-0 pb-2 text-center">
          <div className="mb-4 grid size-12 place-items-center rounded-lg border border-danger/30 bg-danger/10 text-danger">
            <ShieldAlert className="size-6" />
          </div>
          <h2 className="text-xl font-semibold tracking-tight text-foreground">
            Something went wrong while loading this page
          </h2>
          <p className="mt-2 text-sm text-muted">
            An unexpected error occurred during page rendering or data fetching.
          </p>
        </CardHeader>
        <CardContent className="space-y-6 pt-4">
          {error.digest || error.message ? (
            <div className="rounded-md border border-border bg-panel-muted p-3">
              <p className="font-mono text-xs font-semibold text-foreground mb-1">
                Error details:
              </p>
              <code className="block max-h-32 overflow-auto font-mono text-[11px] leading-relaxed text-muted break-all whitespace-pre-wrap">
                {error.digest ? `Digest: ${error.digest}` : error.message}
              </code>
            </div>
          ) : null}
          <div className="flex flex-col sm:flex-row gap-2">
            <Button
              className="flex-1"
              onClick={() => reset()}
              type="button"
              variant="primary"
            >
              Try again
            </Button>
            <Button asChild className="flex-1" variant="secondary">
              <Link href="/">Return to Dashboard</Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
