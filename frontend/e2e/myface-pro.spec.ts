import { expect, test, type Page } from "@playwright/test";
import path from "node:path";

// Parcours complet de MYFACE Pro, sur telephone et sur ordinateur : chaque
// bouton de navigation, le bouton « + », la creation d'un evenement, ses
// onglets, l'envoi d'une photo, les ventes, les notifications, le compte et
// la deconnexion. Compte admin de la copie de test (docker-compose.e2e.yml).
const PHOTO = path.join(__dirname, "fixtures", "photo.jpg");

// Session deja ouverte par auth.setup.ts : on arrive directement sur l'accueil.
async function login(page: Page) {
  await page.goto("/admin");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/Bonjour|Bonsoir/);
}

function isPhone(page: Page): boolean {
  return (page.viewportSize()?.width ?? 1000) < 1024;
}

/** Bouton de navigation : barre du bas sur telephone, menu lateral sinon. */
async function goTo(page: Page, label: "Accueil" | "Événements" | "Ventes" | "Compte" | "Notifications") {
  const nav = page.getByRole("navigation", { name: "Navigation principale" }).filter({ visible: true });
  if (label === "Notifications" && isPhone(page)) {
    await page.getByRole("link", { name: /^Notifications/ }).filter({ visible: true }).first().click();
  } else {
    await nav.getByRole("link", { name: new RegExp(`^${label}`) }).click();
  }
}

test("navigation : chaque onglet ouvre le bon ecran", async ({ page }) => {
  await login(page);
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/Bonjour|Bonsoir/);

  if (isPhone(page)) {
    await expect(page.getByRole("button", { name: "Ajouter des photos ou un événement" })).toBeVisible();
  } else {
    await expect(page.getByRole("button", { name: "Ajouter", exact: true })).toBeVisible();
    await expect(page.getByText("Équipe MYFACE")).toBeVisible();
  }

  await goTo(page, "Événements");
  await expect(page.getByRole("heading", { level: 1, name: "Événements" })).toBeVisible();
  await goTo(page, "Ventes");
  await expect(page.getByRole("heading", { level: 1, name: "Ventes" })).toBeVisible();
  await expect(page.getByText(/À confirmer \(/)).toBeVisible();
  await goTo(page, "Notifications");
  await expect(page.getByRole("heading", { level: 1, name: "Notifications" })).toBeVisible();
  await goTo(page, "Compte");
  await expect(page.getByRole("heading", { level: 1, name: "Compte" })).toBeVisible();
  // Lien de la page Compte (le menu lateral de l'ordinateur a le meme)
  await expect(page.getByRole("link", { name: /Packs à valider/ }).last()).toBeVisible();
  await goTo(page, "Accueil");
  await expect(page).toHaveURL(/\/admin$/);
});

test("evenement : creation par le bouton +, onglets et envoi d'une photo", async ({ page }) => {
  await login(page);
  const name = `Test ${test.info().project.name} ${Date.now()}`;

  if (isPhone(page)) await page.getByRole("button", { name: "Ajouter des photos ou un événement" }).click();
  else await page.getByRole("button", { name: "Ajouter", exact: true }).click();
  await page.getByRole("dialog", { name: "Ajouter" }).getByRole("link", { name: /Créer un événement/ }).click();

  await expect(page.getByRole("heading", { name: "Nouvel événement" })).toBeVisible();
  const dialog = page.locator("form").filter({ has: page.getByRole("heading", { name: "Nouvel événement" }) });
  await dialog.getByPlaceholder("Mariage Aya et Koffi").fill(name);
  await dialog.locator('input[type="datetime-local"]').fill("2026-12-20T18:00");
  await dialog.getByPlaceholder("Abidjan, Cocody").fill("Abidjan");
  await dialog.getByRole("button", { name: "Créer" }).click();

  await expect(page.getByRole("heading", { level: 1, name })).toBeVisible();
  await expect(page.getByRole("tab", { name: "Photos" })).toHaveAttribute("aria-selected", "true");

  // Envoi d'une photo
  await page.locator('input[type="file"]').first().setInputFiles(PHOTO);
  await expect(page.getByText(/^1 photo$/)).toBeVisible({ timeout: 45_000 });

  // Onglets
  await page.getByRole("tab", { name: "Visages" }).click();
  await expect(page.getByText(/regroupés automatiquement/)).toBeVisible();
  await page.getByRole("tab", { name: "Ventes" }).click();
  await expect(page.getByText("Où les invités vous paient")).toBeVisible();
  await expect(page.getByText(/Commandes à confirmer/)).toBeVisible();
  await page.getByRole("tab", { name: "Réglages" }).click();
  await expect(page.getByRole("button", { name: "Supprimer l'événement" })).toBeVisible();
  await expect(page.getByText("Borne de l'événement")).toBeVisible();

  // Haut de page : affiche QR et lien
  await expect(page.getByRole("link", { name: /Affiche QR/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "Copier le lien" })).toBeVisible();

  // Retour a la liste : l'evenement y figure, la recherche le trouve
  await page.getByRole("link", { name: "Retour" }).click();
  await page.getByPlaceholder("Chercher un événement").fill(name);
  await expect(page.getByRole("link", { name: new RegExp(name) })).toBeVisible();
  await page.getByRole("button", { name: "Terminés" }).click();
  await expect(page.getByText("Aucun événement ne correspond.")).toBeVisible();
});

test("compte : installation, aide, deconnexion", async ({ page }) => {
  await login(page);
  await goTo(page, "Compte");
  await expect(page.getByRole("link", { name: /Aide sur WhatsApp/ })).toHaveAttribute("href", /wa\.me/);
  await page.getByRole("link", { name: /Mot de passe et sécurité/ }).click();
  await expect(page.getByRole("heading", { name: "Changer mon mot de passe" })).toBeVisible();
  // Bouton de la page Compte (le menu lateral de l'ordinateur a le meme)
  await page.getByRole("button", { name: /Se déconnecter/ }).last().click();
  await expect(page).toHaveURL(/\/admin\/login/);
});
