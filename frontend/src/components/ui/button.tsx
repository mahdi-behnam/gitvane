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
    "border-transparent bg-primary text-primary-contrast shadow-sm hover:bg-primary/90 hover:shadow-glow dark:bg-primary dark:text-primary-contrast",
  secondary:
    "border-border/80 bg-panel text-foreground shadow-panel hover:bg-panel-muted hover:border-border hover:text-foreground",
  ghost:
    "border-transparent bg-transparent text-muted hover:bg-panel-muted hover:text-foreground",
  danger:
    "border-danger/30 bg-danger/10 text-danger hover:border-danger/50 hover:bg-danger/20",
};

const sizes: Record<ButtonSize, string> = {
  sm: "h-8 gap-2 px-3 text-xs font-semibold",
  md: "h-9 gap-2 px-4 text-sm font-semibold",
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
        "inline-flex shrink-0 items-center justify-center rounded-lg border text-sm transition-all duration-200 ease-out active:scale-[0.97] focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50",
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    />
  );
}

