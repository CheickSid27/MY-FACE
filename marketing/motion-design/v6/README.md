# Motion design v6 : les six scénarios en film (9:16)

Les six scénarios de `../scenarios/scenarios.md`, montés sur leurs voix (`../scenarios/voix/S*.wav`),
avec les règles des compétences `motion-design` (howseen-ai) et `saas-motion-video` (saas-motion-kit),
installées dans `~/.claude/skills/`.

| Film | Fichier | Durée | Pour qui |
|---|---|---|---|
| S1 « Tu as déjà vécu ça ? » | `film_s1.py` | 34 s | invités 18-40 ans |
| S2 « Tantie Aya » (sketch dessiné) | `film_s2.py` | 35,5 s | tout le monde, à partager |
| S3 « Un selfie » | `film_s3.py` | 16 s | statut WhatsApp, TikTok |
| S4 « Organisateurs » | `film_s4.py` | 35,5 s | organisateurs (vouvoiement) |
| S5 « La borne » | `film_s5.py` | 27 s | invités sans smartphone, organisateurs |
| S6 « Photographes » | `film_s6.py` | 29 s | photographes (vouvoiement) |

## Fabriquer

```
python marketing/motion-design/v6/film_s3.py --images      # 4 images de contrôle par scène -> apercus/S3-planche.jpg
python marketing/motion-design/v6/film_s3.py --brouillon   # moitié de taille, 15 i/s, sans flou
python marketing/motion-design/v6/film_s3.py               # films/S3-muet.mp4
python marketing/motion-design/v6/son_v6.py S3             # films/S3-son.wav, films/S3.mp4, films/S3-partage.mp4
```

Un film à la fois : la mémoire du PC est juste quand Docker tourne.

## Ce qui sert

- `moteur_v6.py` : ressorts amortis, caméra (zoom en logarithme), texte qui monte dans un masque,
  transitions (iris, inondation, fouet, bandes, masque de texte, poussée), flou de mouvement ciblé,
  encodage x264 BT.709, planche de contrôle.
- `son_v6.py` : ouverture tendue puis groove à 120 BPM qui tombe sur le moment clé, bruitages posés
  sur les animations, voix découpée par phrase, musique baissée sous la voix, −14 LUFS.
- `phrases_voix.py` : début et fin de chaque phrase des voix (silences).
- `visages_demo.py` : visages trouvés par l'IA de MYFACE sur l'événement de démonstration (API
  publique, lecture seule) -> `visages_demo.json`.
- `captures_demo.mjs` : captures actuelles des écrans invité de la démonstration (Edge sans fenêtre).
- `storyboards/` : message et ton, une ligne par plan ; vérifiés avec
  `python -I ~/.claude/skills/saas-motion-video/tools/variety_audit.py storyboards/S1.md`.

## Règles respectées

- Aucune vente réelle : le graphique de S6 porte « Exemple ».
- Le prix de S5 (700 F, photo et tirage) est le prix par défaut de l'appli, réglé par événement.
- Photos : événement de démonstration (Pexels), jamais présenté comme un client.
  Aucune photo de MA SOUTENANCE (consentement non recueilli).
- Tantie Aya et Koffi sont des dessins : aucune vraie personne ne joue leur rôle.
- Le QR code des films est un vrai code vers l'événement de démonstration.
