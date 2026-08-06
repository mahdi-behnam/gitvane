import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type BadgeTone = "neutral" | "info" | "success" | "warning" | "danger";

const tones: Record<BadgeTone, string> = {
  neutral: "border-border/80 bg-panel-muted/80 text-muted",
  info: "border-primary/25 bg-primary/10 text-primary dark:bg-primary/15",
  success: "border-success/25 bg-success/10 text-success dark:bg-success/15",
  warning: "border-warning/25 bg-warning/10 text-warning dark:bg-warning/15",
  danger: "border-danger/25 bg-danger/10 text-danger dark:bg-danger/15",
};

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: BadgeTone;
};

export function Badge({ className, tone = "neutral", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-[0.1em] transition-colors",
        tones[tone],
        className,
      )}
      {...props}
    />
  );
}

