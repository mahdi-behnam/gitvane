import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        "animate-pulse rounded-md border border-border/60 bg-panel-muted motion-reduce:animate-none",
        className,
      )}
      {...props}
    />
  );
}
