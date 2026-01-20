import js from "@eslint/js";
import tseslint from "typescript-eslint";

export default tseslint.config(
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    ignores: [
      "node_modules/**",
      ".next/**",
      "out/**",
      "components/ui/**", // shadcn auto-generated
      "hooks/use-toast.ts", // shadcn auto-generated
      "next-env.d.ts", // Next.js auto-generated
    ],
  },
  {
    rules: {
      // Allow unused vars prefixed with _
      "@typescript-eslint/no-unused-vars": ["warn", {
        argsIgnorePattern: "^_",
        varsIgnorePattern: "^_"
      }],
      // Allow any type in specific cases
      "@typescript-eslint/no-explicit-any": "warn",
      // Allow require imports in config files
      "@typescript-eslint/no-require-imports": "off",
    },
  }
);
