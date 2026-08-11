/* eslint-disable @next/next/no-img-element */
import { cn } from "@/lib/utils";

export function Logo({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <div className="relative p-1.5 size-9 overflow-hidden rounded-xl border border-border/80 bg-gradient-to-b from-panel to-panel-muted shadow-panel flex items-center justify-center transition-transform hover:scale-105">
        <img
          src="/gitvane-light-logo.png"
          alt="GitVane Icon"
          className="size-full object-contain dark:hidden"
        />
        <img
          src="/gitvane-dark-logo.png"
          alt="GitVane Icon"
          className="hidden size-full object-contain dark:block"
        />
      </div>
      <div>
        <p className="text-sm font-bold tracking-tight leading-none">
          <span className="text-foreground">Git</span>
          <span className="text-primary font-extrabold">Vane</span>
        </p>
        <p className="mt-1 text-[11px] font-medium text-muted/90 tracking-tight">
          Trace change before it spreads.
        </p>
      </div>
    </div>
  );
}

