// Jeton d'acces a une galerie protegee par mot de passe (packs Evenement et
// Pro, voir backend services/gallery_access.py) : obtenu en saisissant le mot
// de passe sur la page d'accueil de l'evenement, garde 7 jours sur cet
// appareil, et ajoute automatiquement par lib/api-client.ts aux appels qui
// montrent des photos (galerie, « Trouver mon visage », selfie).

const KEY_PREFIX = "myface_gallery_access_";

export function getGalleryAccess(eventId: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(KEY_PREFIX + eventId);
  } catch {
    return null;
  }
}

export function rememberGalleryAccess(eventId: string, token: string): void {
  try {
    window.localStorage.setItem(KEY_PREFIX + eventId, token);
  } catch {
    // stockage indisponible (navigation privee) : l'acces vaudra pour cette page seulement
  }
}

export function forgetGalleryAccess(eventId: string): void {
  try {
    window.localStorage.removeItem(KEY_PREFIX + eventId);
  } catch {
    // rien a faire
  }
}

/** Message renvoye par le serveur quand le mot de passe manque. */
export const PASSWORD_REQUIRED_MESSAGE = "Mot de passe de la galerie requis";
