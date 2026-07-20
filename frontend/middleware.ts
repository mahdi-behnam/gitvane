import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const isLoggedInCookie = request.cookies.get("repolens_logged_in");
  const isLoggedIn = isLoggedInCookie?.value === "true";
  const { pathname } = request.nextUrl;

  // If the cookie is present and path matches /login or /signup, redirect to /repositories
  if (isLoggedIn && (pathname === "/login" || pathname === "/signup")) {
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

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/login",
    "/signup",
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
