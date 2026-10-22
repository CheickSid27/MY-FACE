import { expect, test as setup } from "@playwright/test";

// Une seule connexion pour tous les tests : la connexion est limitee a
// quelques essais par minute et par adresse (nginx), les tests reutilisent
// donc la session enregistree ici.
export const ADMIN_STATE = "e2e/.auth/admin.json";

setup("connexion du compte admin de test", async ({ page }) => {
  await page.goto("/admin/login");
  await page.locator('input[type="email"]').fill("admin.e2e@example.com");
  await page.locator('input[type="password"]').fill("E2e-admin-2026");
  await page.locator('button[type="submit"]').click();
  await expect(page).toHaveURL(/\/admin$/);
  await page.context().storageState({ path: ADMIN_STATE });
});
