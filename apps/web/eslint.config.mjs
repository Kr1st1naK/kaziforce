import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    // A second build directory, for an e2e run that has its own server (NEXT_DIST_DIR).
    ".next-*/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Playwright's own output: generated bundles, not source.
    "e2e-report/**",
    "test-results/**",
  ]),
]);

export default eslintConfig;
