"use client";

import { Check, Moon, Monitor, Sun } from "lucide-react";
import { ThemeToggle } from "@/components/app/theme-toggle";
import { useTheme } from "@/components/theme/theme-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { env } from "@/lib/env";

const themeOptions = [
  { icon: Monitor, label: "System", value: "system" as const },
  { icon: Sun, label: "Light", value: "light" as const },
  { icon: Moon, label: "Dark", value: "dark" as const },
];

export default function SettingsPage() {
  const { mode, setMode } = useTheme();

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="border-b border-border pb-6">
        <Badge tone="info">Settings</Badge>
        <h1 className="mt-3 text-3xl font-semibold md:text-4xl">Settings</h1>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold">API base URL</h2>
          </CardHeader>
          <CardContent>
            <code className="block overflow-x-auto rounded-md border border-border bg-panel-muted px-3 py-2 font-mono text-xs text-muted">
              {env.NEXT_PUBLIC_API_BASE_URL}
            </code>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-sm font-semibold">Theme</h2>
              <ThemeToggle />
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid gap-2 sm:grid-cols-3">
              {themeOptions.map((option) => {
                const Icon = option.icon;
                const selected = mode === option.value;

                return (
                  <Button
                    aria-pressed={selected}
                    className="justify-between"
                    key={option.value}
                    onClick={() => setMode(option.value)}
                    type="button"
                    variant={selected ? "secondary" : "ghost"}
                  >
                    <span className="inline-flex items-center gap-2">
                      <Icon aria-hidden="true" className="size-4" />
                      {option.label}
                    </span>
                    {selected ? (
                      <Check aria-hidden="true" className="size-4 text-primary" />
                    ) : null}
                  </Button>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
