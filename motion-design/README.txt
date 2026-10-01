KIT MOTION DESIGN MYFACE
========================

Le telephone et la borne sur fond vert (#00B140), avec les VRAIS ecrans de
l'application dedans, pour animer une main qui touche chaque bouton.

La fiche complete (prompt maitre, 16 plans prets a coller, montage CapCut ou
After Effects) : fiches/sources-html/motion-design-myface.html
et fiches/Motion design MYFACE.pdf

Regenerer le kit (1 minute environ) :

    python motion-design/preparer_motion.py

Il lit :
  - captures/iphone/*.png            ecrans du parcours invite (1206 x 2622)
  - captures/borne/01-accueil.png    accueil de la borne (1080 x 1920)
  - motion-design/sources/3.jpg, 4.jpg   photos de la borne, ecran vert
  - la photo du tirage dans l'evenement de demonstration

Il ecrit (hors git, ces images montrent les photos de la demo) :
  fond-vert/   images de depart pour l'IA (image vers video), 1080 x 1920
  detoure/     les memes sur fond transparent + appareils a ecran vide
  ecrans/      les ecrans seuls, a glisser sous un appareil a ecran vide
  elements/    logo, coins du cadre, onde du toucher, coche, fonds, mur de photos
  guides/storyboard.png   les 16 plans et l'endroit ou le doigt touche

Ecran du telephone dans l'image : x 220, y 221, 640 x 1478 px.

Attention : les captures actuelles viennent de la demo (photos Pexels de vrais
maries). Pour une video diffusee en publicite, refaire les captures sur un vrai
evenement, avec l'accord des maries, puis relancer le script.
