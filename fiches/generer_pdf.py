# -*- coding: utf-8 -*-
"""Transforme les fiches MYFACE en PDF.

Les pages HTML sont dans sources-html/. On leur ajoute une feuille de style
d'impression (fonds conserves, sommaire masque, pas de coupure au milieu
d'une carte), puis Microsoft Edge en mode sans fenetre les imprime en PDF.

Les deux guides en .txt (demarrage du projet, dossier affiches) sont mis en
page avant d'etre imprimes eux aussi.

    python generer_pdf.py

Les PDF sortent dans ce dossier.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
SOURCES = BASE / "sources-html"
PROJET = BASE.parent

NAVIGATEURS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
]

CSS_IMPRESSION = """
<style id="css-impression">
  @page { size: A4; margin: 13mm 11mm 15mm; }
  * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
  html { color-scheme: light; }
  nav.toc, .toc, .band { display: none !important; }
  .layout { display: block !important; padding-bottom: 0 !important; }
  main { max-width: none !important; }
  header.top, header.masthead { padding: 0 0 8px !important; }
  section { padding-top: 26px !important; break-inside: auto; }
  h1 { font-size: 34px !important; }
  h2 { break-after: avoid; }
  h3 { break-after: avoid; }
  table { min-width: 0 !important; }
  .table-wrap { overflow: visible !important; }
  tr, li, p { break-inside: avoid; }
  .regle, .offer, .tac, .copy, .logo-card, .sheet, .summary, .cue, .poster,
  .rules div, .phase, .swatch, .variant, .proof { break-inside: avoid; }
  .copy button { display: none !important; }
  .todo input { -webkit-appearance: none; appearance: none; border: 1.5px solid #9aa; border-radius: 3px; }
  footer.end { break-inside: avoid; }
</style>
"""

GABARIT_TEXTE = """<title>{titre}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Unbounded:wght@600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
  @page {{ size: A4; margin: 15mm 13mm; }}
  * {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
  body {{ background: #F4EFE6; color: #0E2429; margin: 0; padding: 0 0 20px; }}
  header {{ border-bottom: 3px solid #F26A1B; padding-bottom: 10px; margin-bottom: 18px; }}
  .marque {{ font: 700 20px/1 "Unbounded", "Arial Black", sans-serif; letter-spacing: -.02em; }}
  .marque span {{ color: #F26A1B; }}
  h1 {{ font: 600 22px/1.2 "Unbounded", "Arial Black", sans-serif; margin: 10px 0 0; }}
  pre {{ font: 400 12.5px/1.55 "IBM Plex Mono", Consolas, monospace; white-space: pre-wrap;
        margin: 0; color: #22383D; }}
</style>
<header>
  <p class="marque">MY<span>FACE</span></p>
  <h1>{titre}</h1>
</header>
<pre>{contenu}</pre>
"""


def navigateur() -> str:
    for n in NAVIGATEURS:
        if Path(n).exists():
            return n
    raise SystemExit("Ni Edge ni Chrome trouve : impossible de fabriquer les PDF.")


def preparer_html(source: Path, dossier: Path) -> Path:
    html = source.read_text(encoding="utf-8")
    if "</style>" in html:
        html = html.replace("</style>", "</style>" + CSS_IMPRESSION, 1)
    else:
        html = CSS_IMPRESSION + html
    cible = dossier / source.name
    cible.write_text(html, encoding="utf-8")
    return cible


def preparer_texte(source: Path, titre: str, dossier: Path) -> Path:
    contenu = source.read_text(encoding="utf-8", errors="replace")
    contenu = contenu.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    cible = dossier / (source.stem.lower().replace(" ", "-") + ".html")
    cible.write_text(GABARIT_TEXTE.format(titre=titre, contenu=contenu), encoding="utf-8")
    return cible


def imprimer(exe: str, html: Path, pdf: Path) -> None:
    subprocess.run([
        exe, "--headless=new", "--disable-gpu", "--no-sandbox",
        "--no-pdf-header-footer", "--print-to-pdf-no-header",
        "--virtual-time-budget=12000",
        f"--print-to-pdf={pdf}",
        html.resolve().as_uri(),
    ], check=True, capture_output=True, timeout=180)


FICHES = [
    ("linkedin-myface.html", "LinkedIn MYFACE.pdf"),
    ("video-ia-myface.html", "Video IA MYFACE.pdf"),
    ("comment-marche-myface.html", "Comment fonctionne MYFACE.pdf"),
    ("plan-marketing-myface.html", "Plan marketing MYFACE Cote d'Ivoire.pdf"),
    ("kit-lancement-myface.html", "Kit de lancement MYFACE.pdf"),
    ("affiches-myface.html", "Affiches MYFACE - note d'intention.pdf"),
    ("fiche-publication-myface.html", "Fiche de publication MYFACE.pdf"),
    ("fiche-achat-materiel.html", "Fiche d achat du materiel MYFACE.pdf"),
    ("story-whatsapp.html", "Story WhatsApp MYFACE.pdf"),
]

GUIDES = [
    (PROJET / "COMMENT LANCER MYFACE.txt", "Comment lancer MYFACE, de A a Z",
     "Comment lancer MYFACE.pdf"),
    (PROJET / "affiches" / "README.txt", "Le dossier affiches, mode d'emploi",
     "Dossier affiches - mode d'emploi.pdf"),
]


def main():
    exe = navigateur()
    print("Navigateur :", exe)
    with tempfile.TemporaryDirectory() as tmp:
        dossier = Path(tmp)
        # les images du kit (logo) doivent etre a cote de la page
        logos = dossier / "logo"
        logos.mkdir()
        marque = PROJET / "marque"
        for src, dst in [("myface-icone-1-cadre.svg", "cadre.svg"),
                         ("myface-icone-2-masque.svg", "masque.svg"),
                         ("myface-icone-3-obturateur.svg", "obturateur.svg"),
                         ("myface-logo-horizontal.svg", "horizontal.svg"),
                         ("myface-logo-mono-encre.svg", "mono.svg"),
                         ("myface-logo-mono-blanc.svg", "mono-blanc.svg"),
                         ("myface-avatar-1024.png", "avatar.png"),
                         ("myface-avatar-fond-clair-1024.png", "cadre-clair.png")]:
            if (marque / src).exists():
                shutil.copy(marque / src, logos / dst)

        for nom, pdf in FICHES:
            source = SOURCES / nom
            if not source.exists():
                print("  ! manquant :", nom)
                continue
            html = preparer_html(source, dossier)
            imprimer(exe, html, BASE / pdf)
            print(f"  -> {pdf}  ({(BASE / pdf).stat().st_size // 1024} Ko)")

        for source, titre, pdf in GUIDES:
            if not source.exists():
                print("  ! manquant :", source.name)
                continue
            html = preparer_texte(source, titre, dossier)
            imprimer(exe, html, BASE / pdf)
            print(f"  -> {pdf}  ({(BASE / pdf).stat().st_size // 1024} Ko)")

    print("Termine. Les PDF sont dans", BASE)


if __name__ == "__main__":
    main()
