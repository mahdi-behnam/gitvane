"use client";

import {
  Activity,
  BarChart3,
  FlaskConical,
  GitGraph,
  Home,
  Menu,
  RefreshCw,
  Search,
  Server,
  Settings,
  ShieldAlert,
  Waypoints,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { skipToken } from "@reduxjs/toolkit/query";
import { Logo } from "@/components/app/logo";
import { ThemeToggle } from "@/components/app/theme-toggle";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Drawer, DrawerContent, DrawerTrigger } from "@/components/ui/drawer";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useAppSelector } from "@/store/hooks";
import { useGetHealthQuery, useGetRepositoryQuery } from "@/store/api/repolensApi";
import { env } from "@/lib/env";
import { cn } from "@/lib/utils";

const navigationItems = [
  { href: "/", icon: Home, label: "Overview" },
  { href: "/repositories", icon: Waypoints, label: "Repositories" },
  { href: "/repositories/current/search", icon: Search, label: "Search" },
  { href: "/repositories/current/impact", icon: Activity, label: "Impact" },
  { href: "/repositories/current/graph", icon: GitGraph, label: "Graph" },
  { href: "/repositories/current/risk", icon: ShieldAlert, label: "Risk" },
  { href: "/repositories/current/tests", icon: FlaskConical, label: "Tests" },
  {
    href: "/repositories/current/evaluation",
    icon: BarChart3,
    label: "Evaluation",
  },
  { href: "/settings", icon: Settings, label: "Settings" },
];

function isActivePath(pathname: string, href: string) {
  if (href === "/") {
    return pathname === "/";
  }

  return pathname === href || pathname.startsWith(`${href}/`);
}

function NavigationLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <nav aria-label="Primary" className="space-y-1">
      {navigationItems.map((item) => {
        const Icon = item.icon;
        const active = isActivePath(pathname, item.href);

        return (
          <Link
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex h-9 items-center gap-3 rounded-md px-3 text-sm transition",
              active
                ? "bg-panel-muted text-foreground"
                : "text-muted hover:bg-panel-muted hover:text-foreground",
            )}
            href={item.href}
            key={item.href}
            onClick={onNavigate}
          >
            <Icon aria-hidden="true" className="size-4" />
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

function BackendStatus() {
  const health = useGetHealthQuery();
  const healthy = health.data?.status === "healthy";

  return (
    <div className="hidden items-center gap-2 rounded-md border border-border bg-panel px-3 py-2 text-xs text-muted md:flex">
      <Server aria-hidden="true" className="size-4" />
      <span>{health.isLoading ? "Checking backend" : "Backend"}</span>
      <Badge tone={healthy ? "success" : health.error ? "danger" : "neutral"}>
        {healthy ? "Healthy" : health.error ? "Offline" : "Manual"}
      </Badge>
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const activeRepositoryId = useAppSelector(
    (state) => state.repositorySelection.activeRepositoryId,
  );
  const activeRepository = useGetRepositoryQuery(activeRepositoryId ?? skipToken);

  return (
    <TooltipProvider delayDuration={200}>
      <div className="min-h-screen bg-canvas text-foreground">
        <div className="grid min-h-screen lg:grid-cols-[264px_1fr]">
          <aside className="sticky top-0 hidden h-screen border-r border-border bg-panel px-5 py-5 lg:block">
            <Logo />
            <div className="mt-7">
              <NavigationLinks />
            </div>
          </aside>

          <div className="min-w-0">
            <header className="sticky top-0 z-40 border-b border-border bg-canvas/95 px-4 py-3 backdrop-blur-sm sm:px-6 lg:px-8">
              <div className="flex items-center justify-between gap-3">
                <div className="flex min-w-0 items-center gap-3">
                  <div className="lg:hidden">
                    <Drawer>
                      <DrawerTrigger asChild>
                        <Button aria-label="Open navigation" size="icon">
                          <Menu aria-hidden="true" className="size-4" />
                        </Button>
                      </DrawerTrigger>
                      <DrawerContent title="RepoLens">
                        <Logo />
                        <div className="mt-7">
                          <NavigationLinks />
                        </div>
                      </DrawerContent>
                    </Drawer>
                  </div>
                  <div className="min-w-0">
                    <p className="truncate font-mono text-xs uppercase tracking-[0.12em] text-muted">
                      Active repository
                    </p>
                    <p className="truncate text-sm font-medium">
                      {activeRepository.data?.name ?? "None selected"}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <BackendStatus />
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        aria-label="Refresh current view"
                        size="icon"
                        type="button"
                      >
                        <RefreshCw aria-hidden="true" className="size-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Refresh current view</TooltipContent>
                  </Tooltip>
                  <ThemeToggle />
                </div>
              </div>
            </header>

            <div className="border-b border-border bg-panel px-4 py-2 sm:px-6 lg:hidden">
              <nav
                aria-label="Primary shortcuts"
                className="flex gap-1 overflow-x-auto"
              >
                {navigationItems.slice(0, 5).map((item) => {
                  const Icon = item.icon;
                  const active = isActivePath(pathname, item.href);

                  return (
                    <Link
                      aria-current={active ? "page" : undefined}
                      className={cn(
                        "flex min-w-16 flex-col items-center gap-1 rounded-md px-2 py-1.5 text-[11px] hover:bg-panel-muted hover:text-foreground",
                        active ? "text-foreground" : "text-muted",
                      )}
                      href={item.href}
                      key={item.href}
                    >
                      <Icon aria-hidden="true" className="size-4" />
                      {item.label}
                    </Link>
                  );
                })}
              </nav>
            </div>

            <main className="px-4 py-6 sm:px-6 lg:px-8">{children}</main>

            <footer className="border-t border-border px-4 py-4 font-mono text-xs text-muted sm:px-6 lg:px-8">
              API base URL: {env.NEXT_PUBLIC_API_BASE_URL}
            </footer>
          </div>
        </div>
      </div>
    </TooltipProvider>
  );
}
