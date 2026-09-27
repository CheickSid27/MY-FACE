VIDEOS DE DEMONSTRATION MYFACE

  myface-parcours-9x16.mp4        1080x1920, 30 s, 27 Mo  -> TikTok, Reels, stories
  myface-parcours-9x16-leger.mp4   720x1280, 30 s, 11 Mo  -> statut WhatsApp (limite ~16 Mo)
  myface-parcours-1x1.mp4         1080x1080, 30 s, 17 Mo  -> fil Instagram et Facebook

LE DEROULE (8 scenes)
  1. Logo et signature
  2. Les tirages etales par terre : le probleme
  3. Le QR code qu'on scanne
  4. Le selfie, avec le cadre qui se referme sur le visage
  5. Les photos qui apparaissent une a une, avec le compteur
  6. Le paiement : Wave, Orange Money, MTN, especes
  7. Le tirage qui sort de l'imprimante, 500 F
  8. Carte de fin : myfaceci.online et le numero WhatsApp

TOUT EST DESSINE : aucune photo de client, aucun tournage.

POUR MODIFIER (textes, couleurs, duree des scenes)
  python generer_video.py            les trois formats
  python generer_video.py vertical   9:16 seulement
  python generer_video.py leger      720x1280
  python generer_video.py carre      1:1
  Les textes sont dans les fonctions scene_*, la duree de chaque scene est
  dans la liste SCENES en bas du fichier.

A SAVOIR
  Pas de son : ajoute la musique dans CapCut ou directement dans TikTok.
  L'encodage passe par OpenCV en mp4v (pas de H.264 sur ce PC) : les reseaux
  re-encodent de toute facon a la publication.
