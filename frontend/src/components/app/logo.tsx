import { cn } from "@/lib/utils";

export function Logo({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <div className="relative p-1 size-9 overflow-hidden rounded-md border border-border bg-panel-muted flex items-center justify-center">
        <img
          src="/repolens-light-logo.png"
          alt="RepoLens Icon"
          className="size-full object-contain dark:hidden"
        />
        <img
          src="/repolens-dark-logo.png"
          alt="RepoLens Icon"
          className="hidden size-full object-contain dark:block"
        />
      </div>
      <div>
        <p className="text-sm font-semibold leading-none">
          <span className="text-black dark:text-white">Repo</span>
          <span className="text-[#4BA591]">Lens</span>
        </p>
        <p className="mt-1 text-xs text-muted">Trace change before it spreads.</p>
      </div>
    </div>
  );
}
