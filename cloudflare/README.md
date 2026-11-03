# Page « MYFACE revient dans un instant » quand le PC est éteint

Quand le PC qui héberge MYFACE est éteint ou sans internet, Cloudflare affiche sa propre page
d'erreur en anglais (1033 ou 530). Le forfait gratuit de Cloudflare ne permet pas de la remplacer ;
un **Worker** gratuit le peut (100 000 requêtes par jour, largement assez aujourd'hui).

Le Worker (`worker-indisponible.js`) se place devant `app.myfaceci.online` : il laisse passer toutes
les requêtes et ne remplace la réponse que si le tunnel ne répond pas.

Quand le PC est allumé mais l'application arrêtée, c'est nginx qui affiche la même page
(`nginx/erreurs/indisponible.html`).

## Installation (dans le tableau de bord Cloudflare, par le propriétaire du compte)

1. `python cloudflare/generer_worker.py` (refait le fichier si la page a changé).
2. Cloudflare › **Workers & Pages** › **Create** › **Create Worker** › nom : `myface-indisponible` › **Deploy**.
3. **Edit code** : remplacer tout le code par le contenu de `worker-indisponible.js` › **Deploy**.
4. Dans le Worker › **Settings** › **Domains & Routes** › **Add** › **Route** :
   zone `myfaceci.online`, route `app.myfaceci.online/*`, échec : **Fail open** (si le quota est dépassé,
   les requêtes passent normalement).
5. Vérifier : PC allumé, le site marche comme avant ; arrêter le tunnel (`docker compose stop tunnel-domaine`) :
   la page MYFACE s'affiche ; relancer le tunnel.

À ne pas faire : mettre la route sur `myfaceci.online/*` (le site vitrine n'en a pas besoin).
