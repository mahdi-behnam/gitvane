import { Slot } from "@radix-ui/react-slot";
import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonSize = "sm" | "md" | "icon";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  asChild?: boolean;
  variant?: ButtonVariant;
  size?: ButtonSize;
};

const variants: Record<ButtonVariant, string> = {
  primary:
    "border-transparent bg-foreground text-panel hover:bg-foreground/90 dark:bg-foreground dark:text-canvas",
  secondary:
    "border-border bg-panel text-foreground hover:bg-panel-muted hover:text-foreground",
  ghost:
    "border-transparent bg-transparent text-muted hover:bg-panel-muted hover:text-foreground",
  danger:
    "border-danger/30 bg-danger/10 text-danger hover:border-danger/50 hover:bg-danger/15",
};

const sizes: Record<ButtonSize, string> = {
  sm: "h-8 gap-2 px-3 text-xs",
  md: "h-9 gap-2 px-4 text-sm",
  icon: "size-9 p-0",
};

export function Button({
  asChild,
  className,
  size = "md",
  variant = "secondary",
  ...props
}: ButtonProps) {
  const Component = asChild ? Slot : "button";

  return (
    <Component
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-md border font-medium transition duration-150 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50",
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    />
  );
}
