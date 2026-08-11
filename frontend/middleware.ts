import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const isLoggedInCookie = request.cookies.get("gitvane_logged_in");
  const isLoggedIn = isLoggedInCookie?.value === "true";
  const { pathname } = request.nextUrl;

  // If the cookie is present and path matches auth pages, redirect to /repositories
  const authRoutes = ["/login", "/signup", "/forgot-password", "/reset-password"];
  if (isLoggedIn && authRoutes.includes(pathname)) {
    return NextResponse.redirect(new URL("/repositories", request.url));
  }

  // If the cookie is NOT present and path starts with any of the protected routes, redirect to /login
  const protectedRoutes = [
    "/repositories",
    "/settings",
    "/workbench",
    "/risk",
    "/impact",
    "/graph",
    "/tests",
  ];

  const isProtectedRoute = protectedRoutes.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`)
  );

  if (!isLoggedIn && isProtectedRoute) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // Redirect top-level tool routes (/impact, /risk, /graph, /tests, /files) to /repositories/current/...
  const topLevelToolRoutes = ["/impact", "/risk", "/graph", "/tests", "/files"];
  const matchedTool = topLevelToolRoutes.find(
    (tool) => pathname === tool || pathname.startsWith(`${tool}/`)
  );

  if (matchedTool) {
    if (!isLoggedIn) {
      return NextResponse.redirect(new URL("/login", request.url));
    }
    const targetPath = pathname.replace(matchedTool, `/repositories/current${matchedTool}`);
    const redirectUrl = new URL(targetPath, request.url);
    redirectUrl.search = request.nextUrl.search;
    return NextResponse.redirect(redirectUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/login",
    "/signup",
    "/forgot-password",
    "/reset-password",
    "/repositories",
    "/repositories/:path*",
    "/settings",
    "/settings/:path*",
    "/workbench",
    "/workbench/:path*",
    "/risk",
    "/risk/:path*",
    "/impact",
    "/impact/:path*",
    "/graph",
    "/graph/:path*",
    "/tests",
    "/tests/:path*",
  ],
};
