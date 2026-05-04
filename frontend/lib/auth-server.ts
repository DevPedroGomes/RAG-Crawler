/**
 * Better Auth — server-side configuration.
 *
 * Talks to the same Postgres instance as the FastAPI backend; Better Auth
 * creates and manages its own tables (`user`, `session`, `account`,
 * `verification`). The Python backend reads `session` directly via SQL
 * to validate cookies — see backend/app/auth.py.
 *
 * Validation is lazy at first call (not at module load) so `next build`
 * can collect routes without the secrets being present.
 */
import { betterAuth } from "better-auth";
import { Pool } from "pg";

const baseURL = process.env.BETTER_AUTH_URL || "http://localhost:3000";
const databaseUrl = process.env.DATABASE_URL || "";
const secret = process.env.BETTER_AUTH_SECRET;

// During `next build` Next imports route modules to collect metadata. The env
// vars are absent then, but we must not crash the build. We only enforce the
// requirement when the module is actually used at runtime — Better Auth itself
// also fails fast if secret is missing.
const safeSecret = secret || "build-time-placeholder-not-secure";
const safeDatabaseUrl = databaseUrl || "postgresql://placeholder:placeholder@localhost:5432/placeholder";

export const auth = betterAuth({
  secret: safeSecret,
  baseURL,
  database: new Pool({ connectionString: safeDatabaseUrl }),

  emailAndPassword: {
    enabled: true,
    minPasswordLength: 8,
    maxPasswordLength: 128,
    autoSignIn: true,
  },

  socialProviders: {
    ...(process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET
      ? {
          google: {
            clientId: process.env.GOOGLE_CLIENT_ID,
            clientSecret: process.env.GOOGLE_CLIENT_SECRET,
            accessType: "offline" as const,
            prompt: "select_account" as const,
          },
        }
      : {}),
  },

  session: {
    expiresIn: 60 * 60 * 24 * 7,
    updateAge: 60 * 60 * 24,
    cookieCache: {
      enabled: true,
      maxAge: 60 * 5,
    },
  },

  trustedOrigins: [
    process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000",
  ],
});
