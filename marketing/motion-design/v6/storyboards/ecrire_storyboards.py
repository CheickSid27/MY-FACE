# -*- coding: utf-8 -*-
"""Ecrit les storyboards des films v6 au format du saas-motion-kit (message et ton, puis une
ligne par plan), pour que tools/variety_audit.py du kit puisse les verifier.

    python marketing/motion-design/v6/storyboards/ecrire_storyboards.py
    python -I ~/.claude/skills/saas-motion-video/tools/variety_audit.py marketing/motion-design/v6/storyboards/S1.md
"""

from pathlib import Path

ICI = Path(__file__).resolve().parent
ENTETE = ("| # | start | dur | beat | tone | entrance | transition_out | ease | direction | palette | camera | components "
          "| new_component | sfx | notes |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")

FILMS = {
    "S1": ("« Tu as déjà vécu ça ? » (34 s, 9:16)",
           "Je veux dire « tes photos de soirée, retrouvées en un geste » sur un ton urgent puis franc, "
           "pour que l'invité se sente compris puis soulagé.",
           "orange MYFACE (inondation sur « C'est terminé »)", [
               "0:00|6.0|hook|urgent|word-rise-mask|split-stack|expo.out|center|ink+warm-night|handheld-drift|flash, night-photos, grain|motif:flash|flash, shutter|surprise: flash a la premiere image",
               "0:06|6.0|problem|urgent|pill-stretch|motif:cut|expo.in|bottom|sand+ink|locked|chat-phone, counter||notif-rain|surprise: silence sur « Rien. », puis le deluge",
               "0:12|4.0|problem|urgent|slide-from-right|beat-cut-hold|power2.out|right|grey+ink|locked|clock-timelapse, thumb-scroll|clock-timelapse|tick, error|surprise: arret sur image desature avant la coupure",
               "0:16|4.0|reveal|bold|spring-scale|graphic-match-color|spring-heavy|radial|ink+orange-flood|slow-push|logo, flood||impact, whoosh|drop + inondation orange",
               "0:20|4.5|demo|trustworthy|spring-rise|push-through|spring-snappy|from-bottom|orange+sand|locked|qr-table-card, real-gallery, hand|qr-table-card|beep, touch|vrai QR vers la demo",
               "0:24.5|5.5|proof|trustworthy|ring-pulse|focal-iris|io|center|ink+photo|zoom-in-out|real-faces-screen, before-after-wipe||touch, sweep, sparkle|surprise: avant/apres flou net",
               "0:30|4.0|cta|warm|word-rise-mask|end|expo.out|center|ink-pagne|slow-push|logo, words, button||thumps|",
           ]),
    "S2": ("« Tantie Aya » (36 s, 9:16, sketch)",
           "Je veux dire « même Tantie Aya retrouve ses photos avec un selfie » sur un ton joueur et chaleureux, "
           "pour que le spectateur rie et partage.",
           "rouge du foulard + orange MYFACE", [
               "0:00|4.5|hook|playful|bubble-pop|whip-pan|spring-snappy|left|sand-living-room|slow-push|characters, speech-bubbles|lip-sync-characters|pop|bouche calee sur l'energie de la voix",
               "0:04.5|3.5|problem|playful|slide-from-right|motif:whip-pan|expo.out|right|sky-blue|locked|chat-phone, counter||notif-rain|meme geste, sens inverse",
               "0:08|3.5|joke|celebratory|sway|motif:cut|sine|center|warm-orange|beat-punch|dancing-aunt, red-scarf|red-scarf-ribbon|pop|surprise: la danse",
               "0:11.5|7.0|demo|warm|spring-heavy|ink-flood|spring-heavy|from-bottom|sand-living-room|locked|logo-idea, qr-phone, cartoon-selfie||sparkle, beep, shutter|« Voilà ! » sur le flash",
               "0:18.5|4.0|reveal|celebratory|fan-out|motif:cut|back.out|radial|orange-flood|locked|drawn-polaroids, confetti|drawn-polaroids|impact, pops|surprise: drop + confettis",
               "0:22.5|3.5|joke|playful|toss|split-stack|expo.in|right|sand-living-room|locked|flicked-photo||crumple, whoosh|",
               "0:26|7.0|cta|warm|word-rise-mask|end|io|center|sand-pagne|slow-push|logo, stamp|rubber-stamp|impact|surprise: coup de tampon « Y a pas drap »",
           ]),
    "S3": ("« Un selfie » (16 s, 9:16)",
           "Je veux dire « un selfie, deux secondes, toutes tes photos » sur un ton mystérieux puis éclatant, "
           "pour que le spectateur ait envie d'essayer.",
           "orange MYFACE (ligne de balayage)", [
               "0:00|2.0|hook|mysterious|word-rise-mask|motif:cut|expo.out|center|ink-gradient|breathing|viewfinder, shutter, hand||shutter|surprise: flash blanc depuis le bouton",
               "0:02|2.0|build|technical|flash-fade|focal-iris|io|top-down|ink+wall|locked|thumbnail-wall, scan-line, timer|lighting-wall|sweep, ticks|le mur s'allume la ou il est",
               "0:04|3.0|reveal|celebratory|fan-out|whip-pan|spring-heavy|radial|ink+bokeh|dolly-out|card-fan, pill|card-fan|impact, pops|drop de la musique",
               "0:07|4.5|proof|trustworthy|photo-swap|text-mask|spring-snappy|center|photo+ink|locked|searching-frame, grid|searching-frame|thumps on beats|surprise: recul vers la grille des 10",
               "0:11.5|4.5|cta|bold|scale-slam|end|expo.out|center|sand-pagne|slow-push|logo, words||thumps|",
           ]),
    "S4": ("« Organisateurs » (36 s, 9:16, vouvoiement)",
           "Je veux dire « vos invités repartent avec leurs photos, sans que vous vous en occupiez » sur un ton "
           "rassurant et chaleureux, pour que l'organisateur nous écrive.",
           "orange MYFACE, vert du bouton WhatsApp en fin", [
               "0:00|4.5|hook|warm|slide-alternate|split-stack|io|alternate|red+blue+gold|locked|event-bands, flat-icons|flat-icons|whoosh, thumps|",
               "0:04.5|5.5|problem|warm|stack-up|focal-iris|spring-snappy|from-bottom|sand|locked|complaint-stack, calendar|complaint-stack|notifs, paper|surprise: le calendrier qui saute",
               "0:10|5.0|reveal|trustworthy|spring-rise|motif:cut|spring-heavy|radial|ink+bokeh|beat-punch|qr-table-card, beams, three-phones|qr-beams|sparkle, beeps|drop : un QR, trois invites, trois resultats",
               "0:15|3.5|proof|technical|corner-lock|whip-pan|power4.out|left-to-right|photo|dolly-out|real-face-boxes, counter||sweep, beeps|vraies boites de l'IA",
               "0:18.5|7.0|feature|celebratory|toggle|motif:cut|back.out|from-bottom|ink+bokeh|locked|toggle-card, gift-screen, confetti||touch, sparkle|surprise: confettis",
               "0:25.5|3.0|feature|warm|print-slide|ink-flood|io|from-slot|ink+kiosk|push-in|kiosk, print||printer|",
               "0:28.5|3.5|cta|warm|word-rise-mask|end|expo.out|center|ink|slow-push|logo, whatsapp-button, hand||touch|",
           ]),
    "S5": ("« La borne » (28 s, 9:16)",
           "Je veux dire « même sans smartphone, on repart avec sa photo imprimée » sur un ton simple puis fier, "
           "pour que l'organisateur veuille la borne.",
           "orange MYFACE (le prix, le chrono)", [
               "0:00|2.5|hook|calm|strike-through|push-through|io|center|ink|locked|crossed-phone|crossed-phone|error, sparkle|",
               "0:02.5|3.0|demo|warm|spring-rise|focal-iris|power2.out|from-bottom|kiosk-white|slow-zoom|kiosk-camera, hand||touch, shutter|surprise: flash",
               "0:05.5|4.0|proof|trustworthy|grid-pop|motif:cut|spring-snappy|center|kiosk-white|slow-zoom|kiosk-results||sweep, pops|",
               "0:09.5|2.5|action|warm|tap|split-stack|spring-snappy|right|kiosk-white|locked|real-kiosk-screen, hand||touch, beep|",
               "0:12|4.0|price|trustworthy|scale-slam|motif:cut|spring-heavy|center|ink-card|locked|price-card|price-card|till|prix par defaut de l'appli, regle par evenement",
               "0:16|4.5|reveal|celebratory|print-slide|text-mask|io|from-slot|ink+bokeh|beat-punch|print, 20s-ring|20s-ring|printer, ticks|surprise: drop, la photo sort",
               "0:20.5|4.0|cta|warm|word-rise-mask|end|expo.out|center|sand-pagne|slow-push|big-print, logo||thump|",
           ]),
    "S6": ("« Photographes » (29 s, 9:16, vouvoiement)",
           "Je veux dire « déposez, l'IA trie, vos invités achètent » sur un ton direct entre professionnels, "
           "pour que le photographe ouvre son compte.",
           "orange MYFACE, rouge du tampon « INVENDUES »", [
               "0:00|5.0|hook|urgent|gravity-pile|ink-flood|spring-heavy|from-top|wood+desaturated|slow-push|falling-prints, stamp|unsold-stamp|paper, impact|surprise: tampon INVENDUES",
               "0:05|3.0|reveal|bold|flight-arc|motif:cut|io|from-bottom|ink+bokeh|locked|upload-ring, flying-cards||pops|drop de la musique",
               "0:08|4.0|proof|technical|corner-lock|push-through|spring-snappy|left-to-right|photo|locked|real-face-boxes, face-row|face-row|beeps, whoosh|surprise: les visages filent en rang",
               "0:12|3.0|feature|trustworthy|bubble-pop|split-stack|power2.out|from-right|sand|locked|chat-phone, link-card|link-card|whoosh, notif|",
               "0:15|5.0|feature|trustworthy|pill-stretch|motif:cut|spring-snappy|alternate|ink+bokeh|locked|real-cart-screen, payment-pills||pops, till|",
               "0:20|4.0|proof|bold|bar-grow|focal-iris|spring-heavy|from-bottom|ink+cream|slow-push|sales-chart, bursting-bar|bursting-bar|pops, impact|surprise: la derniere barre creve la carte ; marque « Exemple » : aucune vente reelle",
               "0:24|3.0|cta|warm|word-rise-mask|end|expo.out|center|sand-pagne|slow-push|signup-screen, logo||thump|",
           ]),
}

for code, (titre, message, accent, lignes) in FILMS.items():
    rangs = "\n".join(f"| {i + 1} | " + " | ".join(l.split("|")) + " |" for i, l in enumerate(lignes))
    (ICI / f"{code}.md").write_text(
        f"# {code} {titre}\n\n**Message & tone :** {message}\naccent: {accent}\n\n{ENTETE}\n{rangs}\n", encoding="utf-8")
    print(ICI / f"{code}.md")
