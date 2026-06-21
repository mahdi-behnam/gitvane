import { GitBranch } from "lucide-react";
import { cn } from "@/lib/utils";

export function Logo({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <div className="grid size-9 place-items-center rounded-md border border-border bg-panel-muted">
        <GitBranch aria-hidden="true" className="size-4 text-primary" />
      </div>
      <div>
        <p className="text-sm font-semibold leading-none">RepoLens</p>
        <p className="mt-1 text-xs text-muted">Trace change before it spreads.</p>
      </div>
    </div>
  );
}
