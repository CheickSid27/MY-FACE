import { defineConfig } from "@playwright/test";

// Tests de l'interface MYFACE Pro, contre la copie de test isolee
// (docker-compose.e2e.yml, http://localhost:8088 : sa propre base et son
// stockage, jamais la production). Navigateur : Edge deja installe sur le
// PC (aucun navigateur a telecharger).
//
//   docker compose -f docker-compose.e2e.yml -p myface-e2e up -d --build
//   cd frontend && npx playwright test
//   docker compose -f docker-compose.e2e.yml -p myface-e2e down -v
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://localhost:8088",
    channel: "msedge",
    headless: true,
    locale: "fr-FR",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "connexion", testMatch: /auth\.setup\.ts/ },
    {
      name: "telephone",
      dependencies: ["connexion"],
      use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, storageState: "e2e/.auth/admin.json" },
    },
    {
      name: "ordinateur",
      dependencies: ["connexion"],
      use: { viewport: { width: 1366, height: 900 }, storageState: "e2e/.auth/admin.json" },
    },
  ],
});
