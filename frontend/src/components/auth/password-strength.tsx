"use client";

import React from "react";
import { Check, X } from "lucide-react";
import { cn } from "@/lib/utils";

export interface PasswordRule {
  id: string;
  label: string;
  met: boolean;
}

export const SPECIAL_CHARACTERS = "!@#$%^&*()_+-=[]{}|;:,.<>?";

export function getPasswordRules(password: string): PasswordRule[] {
  const specialChars = new Set(SPECIAL_CHARACTERS.split(""));
  const hasSpecial = password.split("").some((char) => specialChars.has(char));

  return [
    {
      id: "length",
      label: "At least 8 characters",
      met: password.length >= 8,
    },
    {
      id: "uppercase",
      label: "At least 1 uppercase letter",
      met: /[A-Z]/.test(password),
    },
    {
      id: "lowercase",
      label: "At least 1 lowercase letter",
      met: /[a-z]/.test(password),
    },
    {
      id: "digit",
      label: "At least 1 digit",
      met: /[0-9]/.test(password),
    },
    {
      id: "special",
      label: `At least 1 special character (${SPECIAL_CHARACTERS})`,
      met: hasSpecial,
    },
  ];
}

export function isPasswordValid(password: string): boolean {
  return getPasswordRules(password).every((rule) => rule.met);
}

interface PasswordStrengthIndicatorProps {
  password?: string;
  className?: string;
}

export function PasswordStrengthIndicator({
  password = "",
  className,
}: PasswordStrengthIndicatorProps) {
  const rules = getPasswordRules(password);
  const metCount = rules.filter((r) => r.met).length;

  return (
    <div
      className={cn("mt-2 rounded-md border border-border/80 bg-panel-muted/50 p-3 text-xs", className)}
      data-testid="password-strength-indicator"
    >
      <div className="flex items-center justify-between text-muted mb-2 font-medium">
        <span>Password requirements:</span>
        <span className="font-mono text-[11px]">
          {metCount}/{rules.length} met
        </span>
      </div>
      <ul className="space-y-1.5" role="list">
        {rules.map((rule) => (
          <li
            key={rule.id}
            className={cn(
              "flex items-center gap-2 transition-colors duration-150",
              rule.met ? "text-success font-medium" : "text-muted opacity-80"
            )}
          >
            {rule.met ? (
              <Check className="size-3.5 shrink-0 text-success" />
            ) : (
              <X className="size-3.5 shrink-0 text-muted/60" />
            )}
            <span>{rule.label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
