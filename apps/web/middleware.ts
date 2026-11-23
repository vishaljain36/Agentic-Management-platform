import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // 1. Explicit bypass for public routes, auth endpoints, static assets, and APIs
  if (
    pathname.startsWith("/login") ||
    pathname.startsWith("/register") ||
    pathname.startsWith("/api") ||
    pathname.startsWith("/_next") ||
    pathname.startsWith("/favicon.ico") ||
    pathname.includes(".") ||
    pathname === "/"
  ) {
    return NextResponse.next();
  }

  // 2. Protected route patterns: /workspace, /admin, or /canvas routes
  const isProtectedRoute =
    pathname.startsWith("/workspace") ||
    pathname.startsWith("/admin") ||
    pathname.includes("/canvas");

  if (isProtectedRoute) {
    const sessionToken =
      request.cookies.get("session_token")?.value ||
      request.headers.get("authorization")?.replace("Bearer ", "");

    if (!sessionToken || sessionToken.trim() === "") {
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("callbackUrl", pathname);
      return NextResponse.redirect(loginUrl, 302);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/workspace/:path*", "/admin/:path*"],
};
