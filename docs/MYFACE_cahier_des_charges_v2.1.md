# MYFACE (AbdShoot) — Roadmap Technique & Cahier des Charges
### Document de référence pour développement par IA (rôle : Lead Dev Senior + Project Manager)
Version 2.1 — Reprise du projet, pivot Web App

---

## 0. INSTRUCTIONS POUR L'IA CHARGÉE DU DÉVELOPPEMENT

Tu agis comme **Lead Developer Senior + Project Manager**. Tes responsabilités :
- Ne jamais livrer de code "mock" ou "démo" sans le signaler explicitement.
- Respecter strictement l'architecture et le stack définis ci-dessous — aucune substitution sans validation.
- Livrer par lots fonctionnels complets (voir Phases), jamais de fragments isolés inutilisables.
- Documenter chaque décision technique qui s'écarte de ce document.
- Chaque fonctionnalité livrée doit être accompagnée de : tests de base, gestion d'erreurs, et validation des entrées.
- Poser une question de clarification plutôt que de supposer, si une spécification est ambiguë.
- Prioriser la sécurité des données biométriques à chaque étape (voir section 8).

---

## 1. VISION DU PRODUIT

**MYFACE** est une plateforme web de reconnaissance faciale permettant aux invités d'événements (mariages, galas, baptêmes, corporate) de retrouver instantanément leurs photos, les acheter et les télécharger — sans intervention manuelle.

**Décision clé de reprise du projet :** le produit devient une **application web responsive** (et non une app mobile installable, ni un client kiosque figé en Flutter). Ce choix garantit la polyvalence :
- Fonctionne sur les **bornes tactiles** installées dans les venues (navigateur en mode kiosque / plein écran)
- Fonctionne sur **smartphone** des invités (ils peuvent scanner via QR code et utiliser leur propre téléphone)
- Fonctionne sur **desktop** pour les organisateurs et photographes (dashboard admin)
- Un seul codebase frontend à maintenir, déployé partout.

---

## 2. PERSONAS & PARCOURS UTILISATEURS

### 2.1 Invité (utilisateur final)
- Arrive à l'événement, voit une borne ou scanne un QR code avec son téléphone
- Deux chemins possibles dès l'écran d'accueil :
  1. **Parcourir la galerie complète** de l'événement (façon Google Photos — grille de miniatures, scroll infini)
  2. **Scanner son visage** pour filtrer directement ses propres photos (utile pour ceux qui sont pressés)
- Sélectionne ses photos, les ajoute au panier
- Paye via Mobile Money (Wave, Orange, MTN, Moov)
- Télécharge immédiatement (lien + QR code) et/ou reçoit un SMS avec le lien

### 2.2 Photographe / Organisateur (admin)
- Se connecte au dashboard
- Crée un événement, génère le token/QR de la borne
- Upload les photos en masse (drag-and-drop, traitement par lots)
- Suit les statistiques en temps réel (photos vues, ventes, revenus)
- Configure la tarification de l'événement (prix unitaire, packs, remises)

---

## 3. ARCHITECTURE TECHNIQUE & STACK

### 3.1 Frontend — Application Web
- **Framework :** React + TypeScript (Next.js recommandé pour SSR/perf + routing)
- **Style :** Tailwind CSS, design responsive mobile-first, mode "kiosque plein écran" activable
- **State management :** Zustand ou Redux Toolkit
- **Composants clés :** grille galerie virtualisée (react-window), capture caméra via `getUserMedia`, panier persistant, écran de paiement avec polling de statut

### 3.2 Backend — API
- **Framework :** Python FastAPI (async)
- **Auth :** JWT pour les comptes admin, tokens HMAC signés pour les sessions borne/invité
- **Structure des routers :** `auth`, `events`, `photos`, `faces`, `cart`, `payments`, `payments/webhook`, `download`, `print`, `admin/stats`

### 3.3 Base de données
- **PostgreSQL** avec extension **pgvector** — stocke les embeddings faciaux directement à côté des lignes utilisateurs/photos (pas de moteur vectoriel séparé type FAISS : simplifie l'infra et les jointures SQL)
- **Index vectoriel : HNSW obligatoire** dès la Phase 2 (pas IVFFlat) — HNSW offre un meilleur compromis vitesse/précision pour de la recherche approximative de plus proche voisin sur des embeddings faciaux, et reste performant même quand le volume de photos par événement grossit (des milliers de visages). Paramètres de départ recommandés : `m = 16`, `ef_construction = 64`, à ajuster après tests de charge (Phase 5).
- Hébergement : Supabase (Postgres managé + Storage + Auth possible)

### 3.4 Reconnaissance faciale
- **InsightFace (ArcFace)** — choix professionnel, haute précision même en cas de visage de profil ou partiellement masqué
- Pipeline : détection de visage → génération d'embedding → recherche de similarité via pgvector (`<->` cosine/L2) → seuil de confiance configurable
- Clustering automatique (DBSCAN) pour pré-grouper les visages inconnus lors de l'upload photographe

**Stratégie de calcul (GPU/CPU) — décision de reprise :**
- **Environnement de dev/test :** GPU local (4 GB VRAM suffisant pour `buffalo_l`, le modèle InsightFace par défaut).
- **Environnement de production :** pas de serveur GPU dédié 24/7 — l'usage est événementiel (pics ponctuels lors des mariages/galas, quasi-nul le reste du temps), donc un GPU dédié serait un gâchis financier. Options à évaluer en Phase 2 :
  - **GPU serverless facturé à l'usage** (RunPod Serverless, Modal, Replicate) : ne coûte que pendant les scans actifs, scalable pendant les pics de fin d'événement.
  - **Fallback CPU** avec modèle allégé (`buffalo_s`) si le budget serverless n'est pas viable, quitte à assouplir légèrement l'objectif de latence.
  - Décision finale à valider avec tests de charge réels avant la Phase 5.

### 3.5 Stockage fichiers
- Supabase Storage (ou S3-compatible) : originaux + miniatures générées (Pillow) + URLs signées à durée limitée

### 3.6 Paiement
- Adaptateurs dédiés par opérateur : **Wave, Orange Money, MTN Money, Moov Money**
- Webhooks avec vérification de signature HMAC
- Statuts : pending → processing → success/failed, avec polling frontend

### 3.7 Notifications
- SMS via **Africa's Talking** (lien de téléchargement, confirmation de paiement)

### 3.8 Infrastructure
- Docker Compose (services : backend, frontend, nginx reverse proxy)
- CI/CD basique (lint + tests + build) avant chaque déploiement

---

## 4. FLUX UTILISATEUR (ÉCRANS)

```
Accueil (QR/borne)
   │
   ▼
Galerie complète de l'événement ──────► Sélection manuelle
   │                                          │
   ▼                                          │
Option "Scanner mon visage"                   │
   │                                          │
   ▼                                          │
Résultats filtrés (mes photos)                │
   │                                          │
   └──────────────► Panier ◄──────────────────┘
                       │
                       ▼
                    Paiement (Mobile Money)
                       │
                       ▼
                  Attente confirmation
                       │
              ┌────────┴────────┐
              ▼                 ▼
           Succès             Échec
      (téléchargement +      (retry /
       SMS + QR download)     support)
```

---

## 5. MODÈLE DE DONNÉES (tables principales)

- **users** : id, rôle (admin/photographe), email, mot de passe hashé, créé le
- **events** : id, nom, date, lieu, token_borne, tarification (JSON), organisateur_id
- **photos** : id, event_id, url_original, url_miniature, uploaded_at, statut_indexation
- **face_embeddings** : id, photo_id, vecteur (pgvector, index HNSW), bounding_box, confiance
- **orders** : id, event_id, contact_invité (téléphone), montant_total, statut, méthode_paiement
- **order_items** : id, order_id, photo_id, prix_unitaire
- **kiosk_sessions** : id, event_id, token, expire_at

---

## 6. ENDPOINTS API (vue d'ensemble)

| Router | Endpoints clés |
|---|---|
| auth | POST /login, POST /refresh |
| events | POST /events, GET /events/{id}, PATCH /events/{id} |
| photos | POST /photos/upload (batch), GET /events/{id}/photos |
| faces | POST /faces/scan (selfie → résultats), GET /faces/status/{photo_id} |
| cart | POST /cart/add, GET /cart/{session_id}, DELETE /cart/{item_id} |
| payments | POST /payments/init, GET /payments/status/{id}, POST /payments/webhook |
| download | GET /download/{order_id} (lien signé + QR) |
| admin/stats | GET /admin/events/{id}/stats |

---

## 7. ROADMAP PAR PHASES

### Phase 1 — Fondations Web App (Semaines 1–3)
- [ ] Setup monorepo (frontend Next.js + backend FastAPI + docker-compose)
- [ ] Auth admin (JWT) + CRUD événements
- [ ] Upload photos (batch, miniatures, stockage Supabase)
- [ ] Écran Accueil + Écran Galerie complète (grille virtualisée, responsive borne/mobile)
- **Livrable :** un événement peut être créé, ses photos uploadées et consultées dans la galerie.

### Phase 2 — Reconnaissance faciale (Semaines 4–6)
- [ ] Intégration InsightFace (détection + embeddings) au moment de l'upload
- [ ] Table pgvector + index HNSW + recherche de similarité
- [ ] Décision GPU serverless vs CPU allégé validée (voir 3.4) et implémentée
- [ ] Écran "Scanner mon visage" (capture caméra web) + résultats filtrés
- [ ] Clustering DBSCAN pour pré-groupage admin (vue "personnes détectées" côté dashboard)
- **Livrable :** un invité peut scanner son visage et voir uniquement ses photos.

### Phase 3 — Panier & Paiement (Semaines 7–9)
- [ ] Panier persistant (session invité)
- [ ] Tarification dynamique (prix unitaire, packs, remises volume) configurable par événement
- [ ] Intégration Wave + Orange Money (priorité 1), puis MTN/Moov (priorité 2)
- [ ] Webhooks + polling statut paiement
- [ ] Génération lien de téléchargement + QR + SMS (Africa's Talking)
- **Livrable :** parcours complet galerie/scan → panier → paiement → téléchargement, fonctionnel de bout en bout.

### Phase 4 — Dashboard Admin & Analytics (Semaines 10–11)
- [ ] Dashboard : liste événements, création, token borne/QR
- [ ] Statistiques temps réel (photos vues, ventes, revenu) — Recharts
- [ ] Gestion utilisateurs/rôles (photographe, staff)

### Phase 5 — Durcissement & Production (Semaines 12–13)
- [ ] Tests de charge (simulation pic d'invités en fin d'événement) — inclut validation finale des paramètres HNSW et de la stratégie GPU/CPU
- [ ] Sécurisation données biométriques (voir section 8)
- [ ] Mode kiosque plein écran + auto-reset après inactivité
- [ ] Déploiement production + monitoring (logs, alertes)

### Phase 6 — Améliorations futures (post-lancement)
- [ ] Impression connectée sur site
- [ ] Historique d'achats par invité (via numéro de téléphone)
- [ ] Multi-événements simultanés sur une même borne
- [ ] Optimisation IA (précision, vitesse de scan < 3 sec)

---

## 8. SÉCURITÉ & CONFORMITÉ

- Consentement explicite avant scan facial (écran dédié, opt-in clair)
- Droit à l'effacement des données biométriques (embeddings) sous 30 jours sur demande
- Chiffrement des embeddings au repos
- URLs de téléchargement signées, à expiration courte
- Vérification stricte des signatures webhook des opérateurs Mobile Money
- Aucune donnée biométrique stockée sur le device borne (tout transite serveur, rien en local persistant)

> ⚠️ **ACTION EN ATTENTE — À NE PAS OUBLIER :** vérifier les obligations légales précises de l'**ARTCI** (Autorité de Régulation des Télécommunications/TIC de Côte d'Ivoire) concernant le traitement de données biométriques (déclaration/autorisation préalable, durée de conservation, droits des personnes concernées). À traiter avant la Phase 5 (mise en production), idéalement avant la Phase 3 (avant toute collecte réelle de données invités). Reporté pour l'instant, mais bloquant avant tout lancement public.

---

## 9. CRITÈRES DE "PROJET SANS BÉMOL"

- Chaque phase livrée = testée manuellement de bout en bout avant de passer à la suivante
- Aucune donnée mockée en Phase 3+ : tout doit venir de la base réelle
- Temps de réponse scan facial < 3 secondes, précision > 95%
- Disponibilité paiement : gestion explicite des échecs/timeouts avec message clair à l'invité
- Interface testée sur au moins 3 formats : borne tactile large, smartphone, desktop admin
