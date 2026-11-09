import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Protected route patterns
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

