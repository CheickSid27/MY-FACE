// Mode borne : active uniquement quand le navigateur charge la page
// evenement avec le vrai `kiosk_token` en query param (?kiosk=...), verifie
// cote serveur (voir backend GET /events/{id}/public). Une fois valide, on
// le garde en sessionStorage pour toute la session de navigation sur cette
// borne — pas besoin de repasser le token sur chaque page (galerie, panier,
// paiement...), et il disparait a la fermeture de l'onglet.
//
// Cash et impression papier n'ont de sens que physiquement sur la borne
// (quelqu'un pour recevoir l'argent, une imprimante branchee) : ce flag
// conditionne leur affichage partout dans l'app, jamais visible sur le
// telephone personnel d'un invite.

function storageKey(eventId: string): string {
  return `myface_kiosk_${eventId}`;
}

export function setKioskMode(eventId: string, isKiosk: boolean): void {
  if (typeof window === "undefined") return;
  try {
    if (isKiosk) {
      window.sessionStorage.setItem(storageKey(eventId), "1");
    } else {
      window.sessionStorage.removeItem(storageKey(eventId));
    }
  } catch {
    // sessionStorage indisponible (navigation privee stricte, etc.) : le
    // mode borne restera simplement desactive, comportement invite normal.
  }
}

export function isKioskMode(eventId: string): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.sessionStorage.getItem(storageKey(eventId)) === "1";
  } catch {
    return false;
  }
}
