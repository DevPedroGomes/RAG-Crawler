"use client";

import { createAuthClient } from "better-auth/react";

const APP_URL = process.env.NEXT_PUBLIC_APP_URL || "";

/**
 * Better Auth client — cookie-based, same-origin (Next.js handles /api/auth).
 * `credentials: include` ensures the session cookie is sent on every fetch.
 */
export const authClient = createAuthClient({
  baseURL: APP_URL || undefined, // same-origin when undefined
  fetchOptions: { credentials: "include" },
});

export const {
  signIn,
  signUp,
  signOut,
  useSession,
  getSession,
} = authClient;
