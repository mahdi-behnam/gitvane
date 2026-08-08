"use client";

import {
  Activity,
  BarChart3,
  FlaskConical,
  GitGraph,
  Home,
  Menu,
  Search,
  Settings,
  ShieldAlert,
  Waypoints,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { usePathname } from "next/navigation";
import React, { useState, useEffect, useRef, type ReactNode } from "react";
import { Logo } from "@/components/app/logo";
import { ThemeToggle } from "@/components/app/theme-toggle";
import { UserMenu } from "@/components/auth/user-menu";
import { Button } from "@/components/ui/button";
import { Drawer, DrawerContent, DrawerTrigger } from "@/components/ui/drawer";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Selector } from "@/components/ui/selector";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
  useListRepositoriesQuery,
  useRefreshMutation,
  useLazyMeQuery,
  useLogoutMutation,
} from "@/store/api/repolensApi";
import { setCredentials, clearCredentials } from "@/store/slices/authSlice";
import { setActiveRepositoryId } from "@/store/slices/repositorySelectionSlice";
import { cn } from "@/lib/utils";

const mainNavItems = [
  { href: "/", icon: Home, label: "Overview" },
  { href: "/repositories", icon: Waypoints, label: "Repositories" },
  { href: "/settings", icon: Settings, label: "Settings" },
];

const repositorySubItems = [
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
];

const navigationItems = [
  mainNavItems[0],
  mainNavItems[1],
  ...repositorySubItems,
  mainNavItems[2],
];

export function parseJwtExp(token: string): number | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const base64Url = parts[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const decodedStr =
      typeof atob === "function"
        ? atob(base64)
        : Buffer.from(base64, "base64").toString("utf-8");
    const parsed = JSON.parse(decodedStr);
    return typeof parsed.exp === "number" ? parsed.exp : null;
  } catch {
    return null;
  }
}

function isActivePath(pathname: string, href: string) {
  if (href === "/") {
    return pathname === "/";
  }

  const normalize = (p: string) =>
    p.replace(/\/repositories\/(?:current|[^/]+)/, "/repositories/current");

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

  const renderItem = (item: { href: string; icon: React.ComponentType<{ className?: string }>; label: string }, isSubItem = false) => {
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
          "relative flex items-center gap-2.5 rounded-lg px-2.5 text-xs font-medium transition-all duration-150",
          isSubItem ? "h-7 text-[11px]" : "h-9 text-xs",
          active
            ? "bg-primary/10 text-primary font-semibold shadow-sm"
            : "text-muted hover:bg-panel-muted/80 hover:text-foreground",
        )}
        href={resolvedHref}
        key={item.href}
        onClick={onNavigate}
      >
        {active && (
          <span className="absolute left-0 top-1.5 bottom-1.5 w-1 rounded-r-full bg-primary" />
        )}
        <Icon aria-hidden="true" className={cn(isSubItem ? "size-3.5 shrink-0" : "size-4 shrink-0", active ? "text-primary" : "text-muted/80")} />
        <span>{item.label}</span>
      </Link>
    );
  };

  return (
    <nav aria-label="Primary" className="space-y-1">
      {mainNavItems.map((item) => {
        if (item.href === "/repositories") {
          return (
            <div key={item.href} className="space-y-1">
              {renderItem(item)}
              <div className="ml-3.5 my-0.5 space-y-0.5 border-l border-border/60 pl-2.5">
                {repositorySubItems.map((subItem) => renderItem(subItem, true))}
              </div>
            </div>
          );
        }
        return renderItem(item);
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

  const accessToken = useAppSelector((state) => state.auth.accessToken);
  const user = useAppSelector((state) => state.auth.user);

  const [refresh] = useRefreshMutation();
  const [triggerMe] = useLazyMeQuery();
  const [logout] = useLogoutMutation();
  const [isInitializing, setIsInitializing] = useState(true);

  const isAuthPage = [
    "/login",
    "/signup",
    "/forgot-password",
    "/reset-password",
    "/auth/callback",
  ].includes(pathname);

  const hasAttemptedRefreshRef = useRef(false);

  useEffect(() => {
    if (isAuthPage) {
      setIsInitializing(false);
      return;
    }

    if (hasAttemptedRefreshRef.current) {
      return;
    }
    hasAttemptedRefreshRef.current = true;

    async function initializeAuth() {
      if (!accessToken) {
        try {
          const tokenRes = await refresh().unwrap();
          dispatch(setCredentials({ accessToken: tokenRes.access_token }));
          
          const userRes = await triggerMe().unwrap();
          dispatch(
            setCredentials({
              accessToken: tokenRes.access_token,
              user: {
                id: userRes.id,
                email: userRes.email,
                full_name: userRes.full_name,
                oauth_provider: userRes.oauth_provider,
                picture: userRes.picture,
              },
            })
          );
        } catch (error) {
          console.error("Silent refresh failed:", error);
          dispatch(clearCredentials());
          document.cookie = "repolens_logged_in=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
          router.replace("/login");
        } finally {
          setIsInitializing(false);
        }
      } else {
        setIsInitializing(false);
      }
    }

    initializeAuth();
  }, [accessToken, refresh, triggerMe, dispatch, isAuthPage, router]);

  useEffect(() => {
    if (!accessToken || isAuthPage) {
      return;
    }

    const exp = parseJwtExp(accessToken);
    const REFRESH_MARGIN_MS = 60 * 1000;
    const DEFAULT_REFRESH_INTERVAL_MS = 10 * 60 * 1000;

    let delayMs = DEFAULT_REFRESH_INTERVAL_MS;
    if (exp) {
      const nowMs = Date.now();
      delayMs = exp * 1000 - nowMs - REFRESH_MARGIN_MS;
      if (delayMs <= 0) {
        delayMs = 1000;
      }
    }

    const timer = setTimeout(async () => {
      try {
        const tokenRes = await refresh().unwrap();
        dispatch(setCredentials({ accessToken: tokenRes.access_token }));
      } catch (err) {
        console.error("Proactive background refresh failed:", err);
      }
    }, delayMs);

    return () => clearTimeout(timer);
  }, [accessToken, isAuthPage, refresh, dispatch]);

  const handleLogout = async () => {
    try {
      await logout().unwrap();
    } catch (err) {
      console.error("Logout failed on server:", err);
    } finally {
      dispatch(clearCredentials());
      document.cookie = "repolens_logged_in=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
      router.replace("/login");
    }
  };

  const handleRepositoryChange = (newId: string | null) => {
    dispatch(setActiveRepositoryId(newId));

    const match = pathname.match(/^\/repositories\/(?:current|[^/]+)(.*)$/);
    if (match) {
      const suffix = match[1];
      if (newId) {
        router.push(`/repositories/${newId}${suffix}`);
      } else {
        router.push(`/repositories/current${suffix}`);
      }
    }
  };

  if (isAuthPage) {
    return <>{children}</>;
  }

  if (isInitializing) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-canvas text-foreground">
        <div className="flex flex-col items-center gap-4">
          <div className="h-9 w-9 animate-spin rounded-full border-3 border-primary border-t-transparent shadow-glow" />
          <p className="text-xs font-semibold text-muted font-mono tracking-wider uppercase">Authenticating...</p>
        </div>
      </div>
    );
  }


  return (
    <TooltipProvider delayDuration={200}>
      <div className="min-h-screen bg-canvas text-foreground">
        <div className="grid min-h-screen lg:grid-cols-[256px_1fr]">
          <aside className="sticky top-0 hidden h-screen flex-col justify-between border-r border-border/80 bg-panel px-4 py-5 lg:flex">
            <div>
              <Logo />
              <div className="mt-8">
                <NavigationLinks />
              </div>
            </div>
            
            <UserMenu
              email={user?.email}
              fullName={user?.full_name}
              oauthProvider={user?.oauth_provider}
              onLogout={handleLogout}
              picture={user?.picture}
            />
          </aside>

          <div className="min-w-0">
            <header className="sticky top-0 z-40 border-b border-border/80 bg-canvas/80 px-4 py-3 backdrop-blur-md sm:px-6 lg:px-8">
              <div className="flex items-center justify-between gap-3">
                <div className="flex min-w-0 items-center gap-3">
                  <div className="lg:hidden">
                    <Drawer>
                      <DrawerTrigger asChild>
                        <Button aria-label="Open navigation" size="icon" variant="secondary">
                          <Menu aria-hidden="true" className="size-4" />
                        </Button>
                      </DrawerTrigger>
                      <DrawerContent title="RepoLens">
                        <div className="flex h-[calc(100%-40px)] flex-col justify-between">
                          <div>
                            <Logo />
                            <div className="mt-7">
                              <NavigationLinks />
                            </div>
                          </div>
                          <UserMenu
                            email={user?.email}
                            fullName={user?.full_name}
                            oauthProvider={user?.oauth_provider}
                            onLogout={handleLogout}
                            picture={user?.picture}
                          />
                        </div>
                      </DrawerContent>
                    </Drawer>
                  </div>
                  <div className="min-w-0">
                    <label
                      className="block truncate font-mono text-[10px] font-bold uppercase tracking-[0.14em] text-muted/80"
                      htmlFor="header-active-repo-select"
                    >
                      Active repository
                    </label>
                    <Selector
                      className="mt-1 w-48 sm:w-52"
                      id="header-active-repo-select"
                      loading={repositories.isLoading}
                      onChange={(val) => {
                        const selectedVal = Array.isArray(val) ? val[0] : val;
                        handleRepositoryChange(selectedVal || null);
                      }}
                      options={[
                        { label: "None selected", value: "" },
                        ...(repositories.data?.items.map((repo) => ({
                          description: repo.default_branch ? `Branch: ${repo.default_branch}` : undefined,
                          label: repo.name,
                          value: repo.id,
                        })) ?? []),
                      ]}
                      placeholder="Select repository..."
                      searchPlaceholder="Filter repos..."
                      value={activeRepositoryId ?? ""}
                    />
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <ThemeToggle />
                </div>
              </div>
            </header>

            <div className="border-b border-border/70 bg-panel px-4 py-2 sm:px-6 lg:hidden">
              <nav
                aria-label="Primary shortcuts"
                className="flex gap-1 overflow-x-auto"
              >
                {navigationItems.slice(0, 5).map((item) => {
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
                        "flex min-w-16 flex-col items-center gap-1 rounded-lg px-2.5 py-1.5 text-[11px] font-medium transition-colors hover:bg-panel-muted hover:text-foreground",
                        active ? "text-primary font-semibold bg-primary/10" : "text-muted",
                      )}
                      href={resolvedHref}
                      key={item.href}
                    >
                      <Icon aria-hidden="true" className="size-4" />
                      {item.label}
                    </Link>
                  );
                })}
              </nav>
            </div>

            <main className="px-4 py-6 sm:px-6 lg:px-8 max-w-7xl mx-auto">{children}</main>

          </div>
        </div>
      </div>
    </TooltipProvider>
  );
}

