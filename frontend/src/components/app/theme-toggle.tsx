"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useTheme } from "@/components/theme/theme-provider";

export function ThemeToggle() {
  const { mode, resolvedMode, setMode, toggleMode } = useTheme();
  const Icon = resolvedMode === "dark" ? Moon : Sun;

  return (
    <TooltipProvider delayDuration={200}>
      <div className="flex items-center rounded-md border border-border bg-panel p-0.5">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              aria-label="Toggle theme"
              className="size-8 border-transparent"
              onClick={toggleMode}
              size="icon"
              type="button"
              variant="ghost"
            >
              <Icon aria-hidden="true" className="size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Toggle theme</TooltipContent>
        </Tooltip>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              aria-label="Use system theme"
              aria-pressed={mode === "system"}
              className="size-8 border-transparent"
              onClick={() => setMode("system")}
              size="icon"
              type="button"
              variant={mode === "system" ? "secondary" : "ghost"}
            >
              <Monitor aria-hidden="true" className="size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Use system theme</TooltipContent>
        </Tooltip>
      </div>
    </TooltipProvider>
  );
}
