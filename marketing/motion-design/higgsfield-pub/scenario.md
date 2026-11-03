# Pub MyFace avec Higgsfield : « La soirée, la borne, le téléphone »

Vidéo verticale 9:16 d'environ 30 s. Personnes réalistes **inventées par l'IA** : aucune vraie personne,
aucun client présenté comme tel. Voix off Zephyr, musique, sous-titres, montage et vrais écrans MyFace
faits avec notre chaîne (`../v6/`).

## Personnages (fiches dans `fiches/`)

- Awa et Ismaël, les mariés (robe de dentelle blanche ; costume bleu roi trois pièces, nœud papillon orange)
- Tantie Aya, invitée (foulard de tête rouge, robe wax bleu et orange, créoles dorées, foulard rouge à la main)
- Yann, jeune invité (chemise de lin beige)
- Le photographe (tout en noir, appareil avec flash)

Décor : salle de réception du soir à Abidjan, voilages blancs, fleurs blanches et orange, guirlandes
lumineuses, tables rondes ; la borne MyFace blanche à anneau lumineux près de l'entrée.

## Plans

| # | Plan | Source | Voix off |
|---|---|---|---|
| 1 | Entrée des mariés, invités debout qui applaudissent (K1) | Higgsfield | « Ce soir, il y a de la joie… » |
| 2 | Le photographe mitraille, Tantie Aya danse avec son foulard (K2) | Higgsfield | « …et des centaines de photos. » |
| 3 | Tantie Aya se tourne vers la caméra de la borne et sourit (K3) | Higgsfield | « Pas besoin de téléphone : la borne MyFace prend un selfie… » |
| 4 | Gros plan : vrai écran de la borne, ses photos apparaissent | captures réelles | « …et l'IA retrouve toutes tes photos. » |
| 5 | Elle brandit le tirage : c'est sa danse du plan 2 (K5) | Higgsfield | « Imprimée sur place. » |
| 6 | Yann scanne le chevalet avec son téléphone (K6) | Higgsfield | « Avec ton téléphone, scanne le QR code… » |
| 7 | Gros plan : vrai écran « Trouver mon visage », puis ses photos | captures réelles | « …touche « Trouver mon visage ». » |
| 8 | Il montre son téléphone à ses amis, les mariés dansent au fond (K8) ; logo, « Scanne. Retrouve. Repars avec. », « Discuter sur WhatsApp » | Higgsfield + fin MyFace | « MyFace. Scanne, retrouve, repars avec. » |

## Règles de cohérence vérifiées sur les images de départ

- Mêmes visages et tenues d'un plan à l'autre (fiches en référence ; modèle Seedream 5.0 Flash).
- La même borne dans les plans 3 et 5 (le plan 3 prend la borne du plan 5 en référence).
- Le tirage du plan 5 montre la danse du plan 2.
- Aucun écran inventé : borne éteinte ou de côté, téléphones de dos, chevalet vu de dos (blanc).
- Tantie Aya n'a pas de téléphone (le message : « pas besoin de téléphone »).
- À recadrer au montage : petit texte parasite en bas à droite de K1.

## Coûts (crédits Higgsfield)

Préparation faite le 29/10 : 7,3 crédits (fiches Soul 2.0, images de départ Seedream 5.0 Flash, reprises).
Reste à faire : animer les 6 plans. Kling 3.0 pro sans son : 8,75 crédits le plan de 5 s, soit environ
53 crédits, 80 avec des reprises. Forfait Starter nécessaire (270 crédits).

`generer_preparation.py` refait les fiches et les plans ; anciennes versions dans `plans/v1/`.
