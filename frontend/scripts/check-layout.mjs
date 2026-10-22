// Garde-fou lance avant chaque construction (npm run build -> prebuild).
//
// Piege constate le 22/10 : une grille CSS (`grid`) qui defile elle-meme
// (`overflow-y-auto`) dans une zone de hauteur fixe (boite de dialogue) ecrase
// ses lignes quand il y a beaucoup de photos : les vignettes se superposent
// (resultats du selfie, 64 photos). Le bon montage : une zone qui defile, et la
// grille A L'INTERIEUR :
//
//   <div className="flex-1 overflow-y-auto p-4">
//     <div className="grid grid-cols-3 gap-2">...</div>
//   </div>
//
// Ce script refuse la construction si une meme balise porte a la fois `grid`
// et `overflow-auto` / `overflow-y-auto`.

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const DIRS = ["app", "components"];
const CLASS_ATTR = /className=(?:"([^"]*)"|\{`([^`]*)`\})/g;

function* files(dir) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) yield* files(path);
    else if (/\.(tsx|jsx)$/.test(name)) yield path;
  }
}

const problems = [];
for (const dir of DIRS) {
  for (const file of files(join(ROOT, dir))) {
    const text = readFileSync(file, "utf8");
    for (const match of text.matchAll(CLASS_ATTR)) {
      const classes = (match[1] ?? match[2]).split(/\s+/);
      const isGrid = classes.includes("grid");
      const scrolls = classes.some((c) => /^overflow(-y)?-(auto|scroll)$/.test(c));
      if (isGrid && scrolls) {
        const line = text.slice(0, match.index).split("\n").length;
        problems.push(`${relative(ROOT, file)}:${line}`);
      }
    }
  }
}

if (problems.length > 0) {
  console.error(
    "Grille qui defile elle-meme (vignettes superposees quand il y a beaucoup de photos).\n" +
      "Mettre la grille DANS une zone qui defile (voir scripts/check-layout.mjs) :\n  " +
      problems.join("\n  ")
  );
  process.exit(1);
}
console.log("check-layout : aucune grille qui defile elle-meme.");
