# -*- coding: utf-8 -*-
"""Fabrique cloudflare/worker-indisponible.js a partir de la page d'erreur de
nginx (nginx/erreurs/indisponible.html), pour que les deux restent identiques.

    python cloudflare/generer_worker.py
"""

import json
from pathlib import Path

ICI = Path(__file__).resolve().parent
PAGE = ICI.parent / "nginx" / "erreurs" / "indisponible.html"
SORTIE = ICI / "worker-indisponible.js"

MODELE = """// GENERE par cloudflare/generer_worker.py a partir de nginx/erreurs/indisponible.html :
// ne pas modifier a la main.
//
// Worker Cloudflare devant app.myfaceci.online. Quand le PC qui heberge MYFACE
// est eteint ou sans internet, Cloudflare montre sa propre page anglaise
// (erreur 1033 ou 530). Ce Worker la remplace par la page MYFACE et, pour les
// appels /api/, par un message JSON que l'application affiche.
// Le forfait gratuit de Cloudflare ne permet pas de personnaliser ses pages
// d'erreur ; un Worker gratuit le peut (100 000 requetes par jour).
// Installation : cloudflare/README.md.

const API_MESSAGE = JSON.stringify({
  detail: "MYFACE est momentanément indisponible. Réessayez dans quelques minutes.",
});

const PAGE = __PAGE__;

function indisponible(request) {
  const headers = { "Retry-After": "30", "Cache-Control": "no-store" };
  if (new URL(request.url).pathname.startsWith("/api/")) {
    return new Response(API_MESSAGE, {
      status: 503,
      headers: { ...headers, "Content-Type": "application/json; charset=utf-8" },
    });
  }
  return new Response(PAGE, { status: 503, headers: { ...headers, "Content-Type": "text/html; charset=utf-8" } });
}

export default {
  async fetch(request) {
    let response;
    try {
      response = await fetch(request);
    } catch {
      return indisponible(request);
    }
    // 530 et 520 a 527 : le tunnel ou le PC ne repond pas. Les 502 a 504 de
    // nginx (PC allume, application arretee) ont deja la page MYFACE.
    if (response.status === 530 || (response.status >= 520 && response.status <= 527)) {
      return indisponible(request);
    }
    return response;
  },
};
"""


def main():
    page = PAGE.read_text(encoding="utf-8")
    SORTIE.write_text(MODELE.replace("__PAGE__", json.dumps(page, ensure_ascii=False)), encoding="utf-8")
    print(SORTIE)


if __name__ == "__main__":
    main()
