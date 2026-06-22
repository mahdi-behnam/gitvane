import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type NoticeTone = "danger" | "info" | "success" | "warning";

const tones: Record<NoticeTone, string> = {
  danger: "border-danger/20 bg-danger/10 text-danger",
  info: "border-primary/20 bg-primary/10 text-primary",
  success: "border-success/20 bg-success/10 text-success",
  warning: "border-warning/20 bg-warning/10 text-warning",
};

type NoticeProps = HTMLAttributes<HTMLDivElement> & {
  tone?: NoticeTone;
};

export function Notice({ className, tone = "info", ...props }: NoticeProps) {
  return (
    <div
      className={cn(
        "rounded-md border px-3 py-2 text-sm leading-6",
        tones[tone],
        className,
      )}
      {...props}
    />
  );
}
