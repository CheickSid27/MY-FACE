// GENERE par cloudflare/generer_worker.py a partir de nginx/erreurs/indisponible.html :
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

const PAGE = "<!doctype html>\n<html lang=\"fr\">\n<head>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n<meta http-equiv=\"refresh\" content=\"30\">\n<meta name=\"robots\" content=\"noindex\">\n<title>MYFACE revient dans un instant</title>\n<style>\n  /* Page servie quand l'application ne repond pas (nginx : 502, 503, 504 ;\n     Worker Cloudflare : PC eteint). Autonome : aucune ressource externe. */\n  :root { --fond: #0E2429; --texte: #F4EFE6; --doux: #A9C3C0; --accent: #F26A1B; }\n  * { box-sizing: border-box; }\n  body {\n    margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center;\n    background: var(--fond); color: var(--texte);\n    font-family: \"Segoe UI\", Roboto, \"Helvetica Neue\", Arial, sans-serif;\n    padding: 24px max(16px, env(safe-area-inset-right, 0px)) 24px max(16px, env(safe-area-inset-left, 0px));\n    text-align: center;\n  }\n  main { max-width: 420px; display: flex; flex-direction: column; align-items: center; gap: 16px; }\n  .logo { font-size: 30px; font-weight: 800; letter-spacing: .02em; }\n  .logo span { color: var(--accent); }\n  .cadre { width: 72px; height: 72px; position: relative; }\n  .cadre i { position: absolute; width: 22px; height: 22px; border-color: var(--accent); border-style: solid; }\n  .cadre i:nth-child(1) { top: 0; left: 0; border-width: 4px 0 0 4px; border-radius: 6px 0 0 0; }\n  .cadre i:nth-child(2) { top: 0; right: 0; border-width: 4px 4px 0 0; border-radius: 0 6px 0 0; }\n  .cadre i:nth-child(3) { bottom: 0; left: 0; border-width: 0 0 4px 4px; border-radius: 0 0 0 6px; }\n  .cadre i:nth-child(4) { bottom: 0; right: 0; border-width: 0 4px 4px 0; border-radius: 0 0 6px 0; }\n  h1 { margin: 8px 0 0; font-size: 24px; line-height: 1.25; }\n  p { margin: 0; color: var(--doux); line-height: 1.5; }\n  .note { font-size: 13px; }\n  a { color: var(--texte); font-weight: 600; }\n  @media (prefers-reduced-motion: no-preference) {\n    .cadre { animation: souffle 2.4s ease-in-out infinite; }\n    @keyframes souffle { 50% { transform: scale(1.06); } }\n  }\n</style>\n</head>\n<body>\n<main>\n  <div class=\"cadre\" aria-hidden=\"true\"><i></i><i></i><i></i><i></i></div>\n  <div class=\"logo\">MY<span>FACE</span></div>\n  <h1>MYFACE revient dans un instant</h1>\n  <p>Le service est momentanément indisponible. Vos photos sont en sécurité et vous attendent.</p>\n  <p class=\"note\">Cette page se recharge toute seule. Vous pouvez aussi <a href=\"\">réessayer maintenant</a>.</p>\n</main>\n</body>\n</html>\n";

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
