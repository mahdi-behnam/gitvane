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
  Settings,
  ShieldAlert,
  Waypoints,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { Logo } from "@/components/app/logo";
import { ThemeToggle } from "@/components/app/theme-toggle";
import { Button } from "@/components/ui/button";
import { Drawer, DrawerContent, DrawerTrigger } from "@/components/ui/drawer";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
  repolensApi,
  useListRepositoriesQuery,
} from "@/store/api/repolensApi";
import { setActiveRepositoryId } from "@/store/slices/repositorySelectionSlice";
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

  const normalize = (p: string) =>
    p.replace(/\/repositories\/(?:current|\d+)/, "/repositories/current");

  const normalizedPathname = normalize(pathname);
  const normalizedHref = normalize(href);

  return (
    normalizedPathname === normalizedHref ||
    normalizedPathname.startsWith(`${normalizedHref}/`)
  );
}

function NavigationLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const activeRepositoryId = useAppSelector(
    (state) => state.repositorySelection.activeRepositoryId,
  );

  return (
    <nav aria-label="Primary" className="space-y-1">
      {navigationItems.map((item) => {
        const Icon = item.icon;
        let resolvedHref = item.href;
        if (item.href.startsWith("/repositories/current/")) {
          const tool = item.href.replace("/repositories/current/", "");
          resolvedHref = activeRepositoryId
            ? `/repositories/${activeRepositoryId}/${tool}`
            : `/repositories/current/${tool}`;
        }

        const active = isActivePath(pathname, resolvedHref);

        return (
          <Link
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex h-9 items-center gap-3 rounded-md px-3 text-sm transition",
              active
                ? "bg-panel-muted text-foreground"
                : "text-muted hover:bg-panel-muted hover:text-foreground",
            )}
            href={resolvedHref}
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

export function AppShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const activeRepositoryId = useAppSelector(
    (state) => state.repositorySelection.activeRepositoryId,
  );
  const repositories = useListRepositoriesQuery();
  const dispatch = useAppDispatch();

  const handleRepositoryChange = (newId: number | null) => {
    dispatch(setActiveRepositoryId(newId));

    const match = pathname.match(/^\/repositories\/(?:current|\d+)(.*)$/);
    if (match) {
      const suffix = match[1];
      if (newId) {
        router.push(`/repositories/${newId}${suffix}`);
      } else {
        router.push(`/repositories/current${suffix}`);
      }
    }
  };

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
                    <label
                      className="block truncate font-mono text-xs uppercase tracking-[0.12em] text-muted"
                      htmlFor="header-active-repo-select"
                    >
                      Active repository
                    </label>
                    <select
                      className="mt-1 block h-8 w-full max-w-[200px] truncate rounded-md border border-border bg-panel px-2 text-xs font-medium text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/20"
                      id="header-active-repo-select"
                      onChange={(event) => {
                        const val = event.target.value;
                        handleRepositoryChange(val ? Number(val) : null);
                      }}
                      value={activeRepositoryId ?? ""}
                    >
                      <option value="">None selected</option>
                      {repositories.data?.items.map((repo) => (
                        <option key={repo.id} value={repo.id}>
                          {repo.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        aria-label="Refresh current view"
                        onClick={() => {
                          dispatch(
                            repolensApi.util.invalidateTags([
                              "Evaluation",
                              "Graph",
                              "Impact",
                              "IndexStatus",
                              "Repository",
                              "Risk",
                            ]),
                          );
                        }}
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


          </div>
        </div>
      </div>
    </TooltipProvider>
  );
}
