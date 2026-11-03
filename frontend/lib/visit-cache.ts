/** Memoire de la visite (pages invites) : ce qui a deja ete charge est
 * reutilise tant que l'onglet est ouvert, pour que revenir a la galerie, a
 * l'accueil de l'evenement ou rouvrir « Trouver mon visage » soit instantane
 * au lieu de repartir vers le serveur (base distante : chaque aller-retour se
 * voit). Les donnees sont gardees peu de temps : de nouvelles photos
 * apparaissent au plus tard apres ce delai. Rien n'est ecrit sur le
 * telephone : tout disparait a la fermeture de l'onglet. */

type Entry = { at: number; promise: Promise<unknown> };

const store = new Map<string, Entry>();

export const VISIT_TTL_MS = 60_000;

export function remember<T>(key: string, load: () => Promise<T>, ttlMs = VISIT_TTL_MS): Promise<T> {
  const now = Date.now();
  const hit = store.get(key);
  if (hit && now - hit.at < ttlMs) return hit.promise as Promise<T>;
  const promise = load();
  store.set(key, { at: now, promise });
  // un echec n'est jamais garde : le prochain essai repart vers le serveur
  promise.catch(() => {
    if (store.get(key)?.promise === promise) store.delete(key);
  });
  return promise;
}

/** Oublie tout ce qui commence par ce prefixe (ex : apres un ajout au panier). */
export function forget(prefix: string): void {
  Array.from(store.keys()).forEach((key) => {
    if (key.startsWith(prefix)) store.delete(key);
  });
}
