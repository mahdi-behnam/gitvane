"use client";

import { useState, type InputHTMLAttributes, type TextareaHTMLAttributes } from "react";
import { Eye, EyeOff } from "lucide-react";
import { cn } from "@/lib/utils";

export function Input({ className, type, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  const [showPassword, setShowPassword] = useState(false);

  const isPassword = type === "password";
  const effectiveType = isPassword ? (showPassword ? "text" : "password") : type;

  if (isPassword) {
    return (
      <div className="relative flex items-center w-full">
        <input
          type={effectiveType}
          className={cn(
            "h-9 w-full rounded-lg border border-border/80 bg-panel pl-3.5 pr-10 text-sm text-foreground placeholder:text-muted/70 transition-all duration-150 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/25 disabled:opacity-50 disabled:bg-panel-muted/80 disabled:cursor-not-allowed",
            className,
          )}
          {...props}
        />
        <button
          type="button"
          tabIndex={-1}
          onClick={() => setShowPassword((prev) => !prev)}
          className="absolute right-3 flex items-center justify-center text-muted hover:text-foreground focus:outline-none transition-colors"
          aria-label={showPassword ? "Hide password" : "Show password"}
        >
          {showPassword ? (
            <EyeOff className="size-4 shrink-0" />
          ) : (
            <Eye className="size-4 shrink-0" />
          )}
        </button>
      </div>
    );
  }

  return (
    <input
      type={type}
      className={cn(
        "h-9 w-full rounded-lg border border-border/80 bg-panel px-3.5 text-sm text-foreground placeholder:text-muted/70 transition-all duration-150 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/25 disabled:opacity-50 disabled:bg-panel-muted/80 disabled:cursor-not-allowed",
        className,
      )}
      {...props}
    />
  );
}

export function Textarea({
  className,
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "min-h-28 w-full rounded-lg border border-border/80 bg-panel px-3.5 py-2.5 text-sm leading-6 text-foreground placeholder:text-muted/70 transition-all duration-150 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/25 disabled:opacity-50 disabled:bg-panel-muted/80 disabled:cursor-not-allowed",
        className,
      )}
      {...props}
    />
  );
}

