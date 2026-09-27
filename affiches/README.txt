=====================================================================
  AFFICHES MYFACE
  Preparees le 27 septembre 2026
=====================================================================

TROIS DOSSIERS, TROIS USAGES
  post\    1080 x 1350  -> publication Instagram et Facebook
  story\   1080 x 1920  -> story, statut WhatsApp, TikTok
  a4\      2480 x 3508  -> impression A4 en 300 dpi (chevalets, affiches)

  sources\ QR codes utilises + planches de controle (pas a publier)

LES AFFICHES  (22 affiches, 37 fichiers)
  A1-signature ......... la marque, trois lignes. A epingler en haut du profil.
  A2-mode-emploi ....... les 3 etapes. Version A4 = chevalet de table.
  A3-telephone ......... l'ecran de l'app sur un iPhone. La preuve que ca existe.
  A4-avant-apres ....... la photo massacree par WhatsApp contre la nette.
  A5-prix .............. la grille de prix + le fait qu'elle change par evenement.
  A6-photographes ...... l'appel aux photographes partenaires (70 %).
  A7-offre-datee ....... l'offre de fin d'annee. La date cree l'urgence.
  A8-pagne-qr .......... affiche partenaire, avec un vrai QR vers un evenement.
  A9-en-4-ecrans ....... les 4 ecrans du parcours, numerotes : montre que
                         tout prend moins d'une minute. Publication, story
                         et A4.
  B1-borne ............. la borne et son fonctionnement en 3 points.
  B2-impression ........ le tirage papier sur place.
  B3-recherche-visage .. le selfie qui remplace le defilement.
  B4-galerie ........... la galerie complete de l'evenement.
  B5-paiement .......... Mobile Money et especes, et le recu detaille.
  B6-telechargement .... qualite d'origine, lien a rouvrir.
  B7-organisateurs ..... ce que voit l'organisateur. A envoyer en prospection.

  C1-organisateurs-forfait . "Offrez leurs photos a vos invites" + forfaits.
  C2-evenement-photographie . A afficher a l'entree : mention droit a l'image
                              + QR pour retrouver ses photos. La plus utile
                              le jour J, et elle nous couvre juridiquement.
  C3-entreprises ....... galas, seminaires, 8 mars, voeux de janvier.
  C4-ecoles ............ remises de diplomes et BDE.
  C5-on-vient-chez-vous  zones couvertes + demande de devis.
  C6-photos-identite ... service de rentree, revenu immediat.

CE QU'IL FAUT CHANGER AVANT DE PUBLIER
  0. Le numero WhatsApp 07 58 50 94 03 est deja en place sur les 8 affiches
     de prospection (A6, A7, B7, C1, C3, C4, C5, C6). S'il change un jour :
     cherche-le dans generer_affiches.py, remplace, et relance le script.
  1. A7 : la date limite de l'offre (30 novembre pour l'instant).
  2. A5 : les prix affiches sont 450 F la photo et +200 F l'impression en
     option, plus la phrase qui rappelle que tout depend de l'evenement.
     A adapter evenement par evenement.
  2 bis. C1 : les forfaits organisateurs (150 000 / 250 000 F) sont des
     points de depart, a valider apres les premiers evenements.
  3. A3, B1, B2, A9 : la borne et le telephone viennent des images fournies
     (fond vert). Le detourage, l'effacement de la marque du fabricant et
     l'incrustation de l'ecran MYFACE sont faits par
     sources/preparer_visuels.py. A relancer si tu fournis de nouvelles
     images :
         python sources/preparer_visuels.py
     puis
         python generer_affiches.py
     Les visuels de borne restent des photos produit du fournisseur : a
     remplacer par une photo de NOTRE borne des qu'on l'a, et a verifier
     qu'il autorise la reutilisation de ses images.
  4. A8 et C2 : le QR pointe vers l'evenement de demonstration
     (https://myfaceci.online/event/af3cfb3c-...). A changer quand tu
     auras un evenement vitrine dedie.

LES IMAGES NE SONT PAS DES PHOTOS DE CLIENTS
  Les visuels sont dessines : silhouettes, halos, degrades. Aucune photo de
  personne reelle n'est utilisee, et rien n'est presente comme un evenement
  MYFACE. C'est volontaire : tant qu'on n'a pas nos propres photos avec
  l'accord des personnes, on ne publie pas de visage.

MODIFIER UNE AFFICHE
  Tout est dans generer_affiches.py (un seul fichier, il faut juste Pillow) :
      python generer_affiches.py
  Les textes sont en bas du fichier, dans la liste AFFICHES. Les couleurs et
  les polices sont en haut. Chaque affiche est une pile de blocs ; le script
  previent si une affiche depasse la page.

  Police des titres : Arial Black (installee sur Windows). Dans Canva, la
  police de la marque est Unbounded, gratuite sur Google Fonts.

COULEURS DE LA MARQUE
  Orange MYFACE  #F26A1B
  Encre lagune   #0E2429
  Sable          #F4EFE6
  Vert d'accent  #00854B
