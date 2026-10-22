import { expect, test } from "@playwright/test";

// Captures d'ecran des ecrans principaux (dossier e2e/captures), pour les
// regarder sans se connecter. Lancees seulement a la demande :
//   CAPTURES=1 npx playwright test captures
test.skip(!process.env.CAPTURES, "captures a la demande seulement");

const SCREENS: [string, string][] = [
  ["accueil", "/admin"],
  ["evenements", "/admin/events"],
  ["ventes", "/admin/ventes"],
  ["notifications", "/admin/notifications"],
  ["compte", "/admin/account"],
];

test("captures des ecrans MYFACE Pro", async ({ page }, info) => {
  for (const [name, url] of SCREENS) {
    await page.goto(url);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `e2e/captures/${info.project.name}-${name}.png`, fullPage: false });
  }
  await page.goto("/admin/events");
  await page.locator('a[href^="/admin/events/"]').first().click();
  await expect(page.getByRole("tab", { name: "Photos" })).toBeVisible();
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `e2e/captures/${info.project.name}-evenement.png`, fullPage: false });
});
