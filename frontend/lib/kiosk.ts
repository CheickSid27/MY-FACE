// Mode borne : active uniquement quand le navigateur charge la page
// evenement avec le vrai `kiosk_token` en query param (?kiosk=...), verifie
// cote serveur (voir backend GET /events/{id}/public). Une fois valide, le
// JETON est garde en sessionStorage pour toute la session de navigation sur
// cette borne, et disparait a la fermeture de l'onglet.
//
// On garde le jeton lui-meme (et pas un simple drapeau "borne = oui") :
// - la page d'accueil le re-verifie aupres du serveur a chaque retour (reset
//   d'inactivite compris) au lieu de perdre le mode borne faute de ?kiosk=
//   dans l'URL — bug corrige : apres le premier reset, la borne redevenait
//   un simple telephone (plus d'especes, plus d'impression, plus de reset) ;
// - il est transmis aux appels publics (galerie, scan, visages) pour que le
//   serveur serve les apercus nets, sans filigrane, a la borne uniquement.
//
// Cash et impression papier n'ont de sens que physiquement sur la borne
// (quelqu'un pour recevoir l'argent, une imprimante branchee) : ce mode
// conditionne leur affichage partout dans l'app, jamais visible sur le
// telephone personnel d'un invite.

function storageKey(eventId: string): string {
  return `myface_kiosk_token_${eventId}`;
}

export function rememberKioskToken(eventId: string, token: string): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(storageKey(eventId), token);
  } catch {
    // sessionStorage indisponible (navigation privee stricte, etc.) : le
    // mode borne restera simplement desactive, comportement invite normal.
  }
}

export function forgetKioskToken(eventId: string): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.removeItem(storageKey(eventId));
  } catch {
    // voir rememberKioskToken
  }
}

export function getKioskToken(eventId: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage.getItem(storageKey(eventId));
  } catch {
    return null;
  }
}

export function isKioskMode(eventId: string): boolean {
  return getKioskToken(eventId) !== null;
}
