// Captures cote invite de l'evenement « MA SOUTENANCE » pour le motion design v5.
// Lecture seule : on ne cree ni panier, ni commande, ni selfie.
// Telephone 430 x 932, densite 3 -> images 1290 x 2796.
//
//   node marketing/motion-design/v5/captures_invite.mjs
// Sorties (hors git, photos de personnes reelles) : marketing/motion-design/v5/captures/

import { mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ICI = dirname(fileURLToPath(import.meta.url));
const require = createRequire(join(ICI, "..", "..", "..", "frontend", "package.json"));
const { chromium } = require("playwright");

const APP = "https://app.myfaceci.online";
const CODE = "TZ6K4DFM";
const SORTIE = join(ICI, "captures");
mkdirSync(SORTIE, { recursive: true });

// Cette version de Playwright ne sait plus lancer les Edge recents (156) : Edge est lance a
// part, sans fenetre, et Playwright s'y connecte.
import { spawn } from "node:child_process";
import { tmpdir } from "node:os";
const PORT = 9333;
const edge = spawn("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe", [
  "--headless=new", `--remote-debugging-port=${PORT}`, "--no-first-run", "--disable-extensions",
  `--user-data-dir=${join(tmpdir(), "edge-captures-myface")}`, "about:blank",
], { stdio: "ignore" });
let browser;
for (let essai = 0; essai < 30 && !browser; essai++) {
  await new Promise((r) => setTimeout(r, 500));
  browser = await chromium.connectOverCDP(`http://127.0.0.1:${PORT}`).catch(() => undefined);
}
if (!browser) throw new Error("Edge ne repond pas");
const context = await browser.newContext({
  viewport: { width: 430, height: 932 },
  deviceScaleFactor: 3,
  isMobile: true,
  hasTouch: true,
  locale: "fr-FR",
});
const page = await context.newPage();

async function imagesChargees() {
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForFunction(() => [...document.images].every((i) => i.complete), null, { timeout: 20000 }).catch(() => {});
  await page.waitForTimeout(900);
}

async function photo(nom) {
  await imagesChargees();
  await page.screenshot({ path: join(SORTIE, `${nom}.png`) });
  console.log("capture", nom);
}

// 0. Accueil de l'application, code tape (sans valider)
await page.goto(APP);
await page.getByPlaceholder("K7M2-QX9P").fill("TZ6K-4DFM");
await photo("00-accueil-code");

// 1. Page d'accueil de l'evenement (lien court)
await page.goto(`${APP}/e/${CODE}`);
await page.getByText("Parcourir la galerie").waitFor({ timeout: 30000 });
await photo("01-accueil-evenement");

// 2. Galerie
await page.getByText("Parcourir la galerie").click();
await page.getByText(/Galerie · \d+ photos/).waitFor({ timeout: 30000 });
await page.waitForTimeout(2500);
await photo("02-galerie");

// 3. Trouver mon visage
await page.getByRole("button", { name: "Trouver mon visage" }).click();
await page.getByText("Personne 1", { exact: false }).first().waitFor({ timeout: 60000 }).catch(() => {});
await page.waitForTimeout(2500);
await photo("03-trouver-mon-visage");

// 4. Photos d'une personne (le plus grand groupe : premier de la liste)
await page.locator('img[alt="Personne 1"]').first().click();
await page.waitForTimeout(2500);
await photo("04-photos-personne");

// 5. Visionneuse (photo avec filigrane)
// la premiere photo de la boite « Personne 1 » (pas la galerie derriere)
const boite = page.locator("div.overflow-y-auto", { hasText: /Personne 1, \d+ photo/ }).last();
await boite.locator("img").nth(2).click();
await page.waitForTimeout(3500);
await photo("05-visionneuse");

// 6. Inscription photographe (page publique)
await page.goto(`${APP}/photographes/inscription`);
await photo("06-inscription-photographe");

await browser.close();
edge.kill();
