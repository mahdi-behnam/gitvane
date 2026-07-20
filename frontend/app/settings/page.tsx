"use client";

import { Check, Moon, Monitor, Sun } from "lucide-react";
import { ThemeToggle } from "@/components/app/theme-toggle";
import { useTheme } from "@/components/theme/theme-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
  setDependencyDepth,
  setIncludeChangedFilesInImpact,
  setIncludeExplanations,
} from "@/store/slices/appPreferencesSlice";

const themeOptions = [
  { icon: Monitor, label: "System", value: "system" as const },
  { icon: Sun, label: "Light", value: "light" as const },
  { icon: Moon, label: "Dark", value: "dark" as const },
];

export default function SettingsPage() {
  const { mode, setMode } = useTheme();
  const dispatch = useAppDispatch();
  const preferences = useAppSelector((state) => state.appPreferences);

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="border-b border-border pb-6">
        <Badge tone="info">Settings</Badge>
        <h1 className="mt-3 text-3xl font-semibold md:text-4xl">Settings</h1>
      </div>

      <div className="max-w-2xl space-y-6">
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

        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold">Analysis & Impact Preferences</h2>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-2">
              <label
                className="block text-sm font-medium"
                htmlFor="settings-dependency-depth"
              >
                Default Max Dependency Depth
              </label>
              <p className="text-xs text-muted">
                Maximum graph depth for dependency traversal when analyzing change impact.
              </p>
              <Input
                className="max-w-[120px]"
                id="settings-dependency-depth"
                max={10}
                min={1}
                onChange={(event) =>
                  dispatch(setDependencyDepth(Math.max(1, Number(event.target.value))))
                }
                type="number"
                value={preferences.dependencyDepth}
              />
            </div>

            <div className="space-y-3 pt-2">
              <label className="flex items-start gap-3 text-sm">
                <input
                  checked={preferences.includeChangedFilesInImpact}
                  className="mt-1 rounded border-border text-primary focus:ring-primary"
                  onChange={(event) =>
                    dispatch(setIncludeChangedFilesInImpact(event.target.checked))
                  }
                  type="checkbox"
                />
                <div>
                  <span className="font-medium text-foreground">
                    Include changed files in predictions
                  </span>
                  <p className="text-xs text-muted">
                    When enabled, the changed files themselves will be included alongside predicted impact files.
                  </p>
                </div>
              </label>

              <label className="flex items-start gap-3 text-sm">
                <input
                  checked={preferences.includeExplanations}
                  className="mt-1 rounded border-border text-primary focus:ring-primary"
                  onChange={(event) =>
                    dispatch(setIncludeExplanations(event.target.checked))
                  }
                  type="checkbox"
                />
                <div>
                  <span className="font-medium text-foreground">
                    Generate LLM analysis explanations
                  </span>
                  <p className="text-xs text-muted">
                    Request evidence-based explanation summaries alongside impact analysis runs.
                  </p>
                </div>
              </label>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
