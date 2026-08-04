"use client";

import React from "react";
import { Info } from "lucide-react";
import { TooltipProvider, Tooltip, TooltipTrigger, TooltipContent } from "./tooltip";
import { cn } from "@/lib/utils";

interface TermTooltipProps {
  id?: string;
  term?: string;
  description: string;
  children?: React.ReactNode;
  className?: string;
  iconClassName?: string;
}

export function TermTooltip({
  id,
  term,
  description,
  children,
  className,
  iconClassName,
}: TermTooltipProps) {
  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <span className={cn("inline-flex items-center gap-1.5", className)}>
          {children || (term && <span id={id}>{term}</span>)}
          <TooltipTrigger asChild>
            <button
              type="button"
              className="inline-flex items-center justify-center rounded text-muted hover:text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
              aria-label={term ? `More information about ${term}` : "More information"}
            >
              <Info className={cn("size-3.5 shrink-0 opacity-70 hover:opacity-100 transition-opacity", iconClassName)} />
            </button>
          </TooltipTrigger>
        </span>
        <TooltipContent className="max-w-xs text-xs leading-normal bg-panel border border-border shadow-md p-2.5">
          {description}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
