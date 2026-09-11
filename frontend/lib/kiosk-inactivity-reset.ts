"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { clearCartSessionId } from "@/lib/cart";

const KIOSK_INACTIVITY_MS = 90_000;

// Reinitialise le panier de la borne apres une periode d'inactivite, pour
// qu'un client qui selectionne des photos puis s'en va sans payer ne laisse
// pas son panier "actif" pour le client suivant sur la meme borne partagee
// (celui-ci verrait sinon les selections/le panier du client precedent en
// arrivant sur la galerie, avec un risque reel de payer les photos de
// quelqu'un d'autre). Sans effet sur le telephone personnel d'un invite
// (`active` = mode borne uniquement) : on ne veut surtout pas effacer le
// panier d'un vrai client qui prend son temps sur son propre appareil.
//
// Le retour se fait vers l'accueil sans ?kiosk= dans l'URL : l'accueil
// re-verifie le jeton borne memorise (lib/kiosk.ts), la borne reste donc
// une borne pour le client suivant.
export function useKioskInactivityReset(eventId: string, active: boolean) {
  const router = useRouter();
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!active) return;

    function reset() {
      clearCartSessionId(eventId);
      router.push(`/event/${eventId}`);
    }

    function bump() {
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(reset, KIOSK_INACTIVITY_MS);
    }

    const events = ["pointerdown", "keydown", "scroll", "touchstart"];
    events.forEach((evt) => window.addEventListener(evt, bump));
    bump();

    return () => {
      events.forEach((evt) => window.removeEventListener(evt, bump));
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [active, eventId, router]);
}
