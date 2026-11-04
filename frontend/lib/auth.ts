// La session vit dans des cookies proteges poses par le serveur (HttpOnly :
// illisibles par le code de la page, voir backend services/session_cookies).
// Le navigateur ne garde ici qu'un indicateur « connecte », sans aucun secret,
// pour savoir s'il faut afficher l'espace MYFACE Pro ou la page de connexion.
const SESSION_FLAG = "myface_session";
// Anciennes cles (jetons en clair) : effacees au chargement.
const LEGACY_KEYS = ["myface_access_token", "myface_refresh_token"];

function storage(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

if (typeof window !== "undefined") {
  const s = storage();
  LEGACY_KEYS.forEach((k) => s?.removeItem(k));
}

export function markLoggedIn(): void {
  storage()?.setItem(SESSION_FLAG, "1");
}

export function clearSession(): void {
  storage()?.removeItem(SESSION_FLAG);
}

export function isAuthenticated(): boolean {
  return storage()?.getItem(SESSION_FLAG) === "1";
}
