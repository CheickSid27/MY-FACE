# Integration continue

Deux workflows, ajoutes sans toucher au reste du depot. Aucun fichier
applicatif (`backend/`, `frontend/`, `nginx/`, `docker-compose*.yml`,
`.env.example`) n'a ete modifie.

## `tests.yml` — a chaque push et chaque pull request

| Job | Ce qu'il fait | Peut-il faire echouer ? |
|---|---|---|
| Backend | Lance `pytest` contre un vrai PostgreSQL `pgvector/pgvector:pg16`, comme en local | **Oui** |
| Backend | `ruff check` | Non, informatif seulement |
| Frontend | `npx tsc --noEmit` (tsconfig en mode strict) | **Oui** |
| Frontend | `node scripts/check-layout.mjs` | Non, informatif seulement |

Pourquoi `ruff` n'est pas bloquant : le code existant remonte aujourd'hui
345 ecarts. Les rendre bloquants mettrait le depot au rouge immediatement.
Le rapport s'affiche dans l'onglet Actions, annote directement sur les lignes
concernees. Pour les traiter progressivement :

```bash
cd backend
ruff check . --statistics      # voir les familles d'erreurs les plus frequentes
ruff check . --fix             # 141 sont corrigeables automatiquement
```

Le jour ou le compte tombe a zero, retirez `continue-on-error: true` de l'etape
« Lint » pour le rendre bloquant.

### Pourquoi la CI n'utilise pas l'image Docker du backend

`backend/Dockerfile` part de `nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04`,
soit plusieurs Go, pour un GPU que les serveurs GitHub n'ont pas. La CI
installe donc les dependances directement et remplace `onnxruntime-gpu` par
`onnxruntime` (CPU) **a la volee, dans le workflow uniquement** —
`requirements.txt` n'est pas modifie.

Ce n'est pas une perte de couverture : la suite de tests ne charge aucun modele
InsightFace et remplace le stockage par un double en memoire
(`InMemoryStorageService` dans `backend/tests/conftest.py`).

### Variables utilisees par la CI

Aucune n'est secrete, ce sont des valeurs jetables du runner :

```
SECRET_KEY        cle-de-test-ci-sans-valeur-en-production
DATABASE_URL      postgresql+asyncpg://myface:myface@localhost:5432/myface
TEST_DATABASE_URL postgresql+asyncpg://myface:myface@localhost:5432/myface_test
```

La suite tourne toujours contre `myface_test`, jamais contre Neon.

## `revue-claude.yml` — a chaque pull request

Claude relit le diff et commente les problemes reels : controle d'acces
manquant, fuite d'embeddings faciaux ou de selfie, filigrane contourne, original
accessible sans commande payee, erreur de prix, requete non bornee par
`event_id`, migration destructrice. Il a pour consigne de ne pas commenter le
style.

**Ce workflow est inactif tant que vous n'avez pas ajoute le secret.** Sans cle,
il se termine en succes avec une simple note. Pour l'activer :

1. Generez une cle sur https://console.anthropic.com/settings/keys
2. Depot > **Settings** > **Secrets and variables** > **Actions** > **New repository secret**
3. Nom : `ANTHROPIC_API_KEY`, valeur : la cle

Attention : le depot etant public, les pull requests venant d'un fork n'ont pas
acces aux secrets. La revue ne s'executera que sur les branches du depot.
