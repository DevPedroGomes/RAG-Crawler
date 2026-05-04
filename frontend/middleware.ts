import { NextRequest, NextResponse } from "next/server";

/**
 * Lightweight auth gate. Better Auth issues an httpOnly cookie named
 * `better-auth.session_token` (or `__Secure-better-auth.session_token` over
 * HTTPS in production). The middleware just checks for its presence —
 * cryptographic validation happens in the Better Auth handler at
 * /api/auth and again at the FastAPI backend (see backend/app/auth.py).
 *
 * Public routes: home, sign-in/up, the auth handler, and Next assets.
 */
const PUBLIC_PATHS = new Set(["/", "/sign-in", "/sign-up"]);

function isPublicPath(pathname: string): boolean {
  if (pathname.startsWith("/_next/")) return true;
  // Better Auth routes — handler validates internally.
  if (pathname.startsWith("/api/auth/")) return true;
  // Backend proxy — auth is enforced in FastAPI via the session cookie,
  // so the middleware does not double-gate.
  if (pathname.startsWith("/api/backend/")) return true;
  if (PUBLIC_PATHS.has(pathname)) return true;
  if (pathname.startsWith("/sign-in/")) return true;
  if (pathname.startsWith("/sign-up/")) return true;
  return false;
}

export function middleware(request: NextRequest) {
  if (isPublicPath(request.nextUrl.pathname)) {
    return NextResponse.next();
  }

  const sessionCookie =
    request.cookies.get("__Secure-better-auth.session_token") ??
    request.cookies.get("better-auth.session_token");

  if (!sessionCookie?.value) {
    const signIn = new URL("/sign-in", request.url);
    signIn.searchParams.set("callbackUrl", request.nextUrl.pathname);
    return NextResponse.redirect(signIn);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
  ],
};
