"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import FindFacesDialog from "@/components/faces/FindFacesDialog";
import Pagination from "@/components/gallery/Pagination";
import PhotoGrid from "@/components/gallery/PhotoGrid";
import PhotoLightbox from "@/components/gallery/PhotoLightbox";
import { CameraIcon, CartIcon, UsersIcon } from "@/components/icons";
import ScanDialog from "@/components/scan/ScanDialog";
import { api } from "@/lib/api-client";
import { getCartSessionId, setCartSessionId } from "@/lib/cart";
import { useKioskInactivityReset } from "@/lib/kiosk-inactivity-reset";
import { getKioskToken, isKioskMode } from "@/lib/kiosk";
import type { CartRead, Photo, PhotoListResponse } from "@/types/api";

const PAGE_SIZE = 60;

export default function GalleryPage() {
  const { eventId } = useParams<{ eventId: string }>();
  const router = useRouter();
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [frameCaption, setFrameCaption] = useState<string | null>(null);
  const [kiosk, setKiosk] = useState(false);

  useEffect(() => {
    api
      .getEventPublic(eventId)
      .then((event) => setFrameCaption(event.frame_caption))
      .catch(() => {
        // cadre decoratif optionnel : silencieux si l'evenement est introuvable ici
      });
  }, [eventId]);

  useEffect(() => {
    setKiosk(isKioskMode(eventId));
  }, [eventId]);

  useKioskInactivityReset(eventId, kiosk);

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [itemIdByPhoto, setItemIdByPhoto] = useState<Record<string, string>>({});
  const [cartCount, setCartCount] = useState(0);
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);
  const [scanOpen, setScanOpen] = useState(false);
  const [findFacesOpen, setFindFacesOpen] = useState(false);
  const cartIconRef = useRef<HTMLButtonElement>(null);

  function bumpCartIcon() {
    const el = cartIconRef.current;
    if (!el) return;
    el.classList.remove("animate-cart-bump");
    void el.offsetWidth;
    el.classList.add("animate-cart-bump");
  }

  // Cache en memoire par page : la latence vient surtout de l'aller-retour
  // reseau vers la base geree (Neon, distante), pas du chargement des images.
  // On pre-charge silencieusement la page suivante des qu'une page s'affiche,
  // pour que le clic "suivant" (le parcours le plus courant) semble instantane
  // la plupart du temps au lieu d'attendre ~0.5-1s a chaque fois.
  const pageCacheRef = useRef<Map<number, PhotoListResponse>>(new Map());

  useEffect(() => {
    pageCacheRef.current.clear();
  }, [eventId]);

  const fetchAndCache = useCallback(
    async (pageToLoad: number) => {
      // Jeton borne transmis : le serveur sert alors les apercus nets ; sur
      // le telephone d'un invite, ils sont filigranes (voir lib/kiosk.ts).
      const data = await api.listPhotos(eventId, pageToLoad, PAGE_SIZE, getKioskToken(eventId));
      pageCacheRef.current.set(pageToLoad, data);
      return data;
    },
    [eventId]
  );

  // Pagination numerotee (pas d'accumulation "charger plus") : chaque page
  // remplace entierement la precedente, la grille virtualisee redemarre donc
  // toujours en haut sans etat de scroll a restaurer.
  const loadPage = useCallback(
    async (pageToLoad: number) => {
      const cached = pageCacheRef.current.get(pageToLoad);
      if (!cached) setLoading(true);
      try {
        const data = cached ?? (await fetchAndCache(pageToLoad));
        setPhotos(data.items);
        setTotal(data.total);
        setPage(pageToLoad);
      } catch {
        setError("Impossible de charger la galerie.");
      } finally {
        setLoading(false);
      }
    },
    [fetchAndCache]
  );

  useEffect(() => {
    loadPage(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventId]);

  useEffect(() => {
    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    const next = page + 1;
    if (next <= totalPages && !pageCacheRef.current.has(next)) {
      fetchAndCache(next).catch(() => {
        // pre-chargement best-effort : un echec ici sera simplement retente au clic reel
      });
    }
  }, [page, total, fetchAndCache]);

  function syncCart(cart: CartRead) {
    // Les ajouts encore dans le lot en attente (debounce, pas encore envoyes)
    // ne sont pas dans le panier serveur : on les conserve, sinon une
    // resynchronisation effacerait visuellement une selection toute recente
    // (meme cause que le "flicker" corrige le 01/09, voir handleToggleSelect).
    const selected = new Set(cart.items.map((item) => item.photo.id));
    pendingAddIdsRef.current.forEach((id) => selected.add(id));
    setSelectedIds(selected);
    setCartCount(selected.size);
    const map: Record<string, string> = {};
    cart.items.forEach((item) => {
      map[item.photo.id] = item.id;
    });
    setItemIdByPhoto(map);
  }

  const reloadCart = useCallback(() => {
    const sessionId = getCartSessionId(eventId);
    if (!sessionId) return;
    api
      .getCart(sessionId)
      .then(syncCart)
      .catch(() => {
        // panier expire ou introuvable : on repart d'un panier vide
      });
  }, [eventId]);

  useEffect(() => {
    reloadCart();
  }, [reloadCart]);

  // Le dialogue de scan gere son propre panier (ajouts/retraits depuis les
  // resultats) : la galerie se resynchronise sur le serveur apres chacune de
  // ses modifications, sinon le badge et les coches restaient perimes a la
  // fermeture du dialogue. Rechargement regroupe (debounce) : une serie de
  // clics rapides ne declenche qu'un seul aller-retour.
  const reloadTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const scheduleCartReload = useCallback(() => {
    if (reloadTimerRef.current) clearTimeout(reloadTimerRef.current);
    reloadTimerRef.current = setTimeout(reloadCart, 300);
  }, [reloadCart]);

  useEffect(
    () => () => {
      if (reloadTimerRef.current) clearTimeout(reloadTimerRef.current);
    },
    []
  );

  const itemIdByPhotoRef = useRef<Record<string, string>>({});
  itemIdByPhotoRef.current = itemIdByPhoto;
  const selectedIdsRef = useRef<Set<string>>(selectedIds);
  selectedIdsRef.current = selectedIds;

  // Ajouts groupes plutot qu'une requete reseau par clic : une selection
  // rapide de plusieurs photos accumule leurs IDs ici, et une seule requete
  // /cart/add-bulk part apres un court debounce (ou immediatement si on va
  // au panier ou qu'on utilise "tout selectionner") au lieu d'une requete
  // sequentielle par photo, sur une base distante (~0.5-1s l'aller-retour),
  // dix clics rapides attendaient auparavant dix aller-retours l'un derriere
  // l'autre avant que "voir le panier" ne parte reellement.
  const FLUSH_DEBOUNCE_MS = 500;
  const pendingAddIdsRef = useRef<Set<string>>(new Set());
  const flushTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Chaine les flush entre eux (pas les clics individuels) : evite que deux
  // flush groupes concurrents ne creent chacun leur propre session panier
  // avant que le premier n'ait pu renvoyer le session_id au second.
  const flushChainRef = useRef<Promise<void>>(Promise.resolve());
  // Suppressions en cours (immediates, pas debouncees) : "aller au panier"
  // doit aussi les attendre, sinon meme probleme que pour les ajouts mais a
  // l'envers (une photo deselectionnee juste avant de payer pourrait rester
  // facturee si on navigue avant que le DELETE n'ait ete confirme).
  const pendingRemovesRef = useRef<Promise<void>[]>([]);

  const flushPendingAdds = useCallback((): Promise<void> => {
    if (flushTimerRef.current) {
      clearTimeout(flushTimerRef.current);
      flushTimerRef.current = null;
    }
    if (pendingAddIdsRef.current.size === 0) return flushChainRef.current;

    const ids = Array.from(pendingAddIdsRef.current);
    pendingAddIdsRef.current = new Set();

    flushChainRef.current = flushChainRef.current.then(async () => {
      try {
        const sessionId = getCartSessionId(eventId);
        const cart = await api.addToCartBulk(eventId, ids, sessionId);
        setCartSessionId(eventId, cart.session_id);
        const newMap: Record<string, string> = {};
        cart.items.forEach((item) => {
          newMap[item.photo.id] = item.id;
        });
        setItemIdByPhoto((prev) => ({ ...prev, ...newMap }));
      } catch {
        setSelectedIds((prev) => {
          const next = new Set(prev);
          ids.forEach((id) => next.delete(id));
          return next;
        });
        setCartCount((c) => Math.max(0, c - ids.length));
        setError("Impossible de mettre à jour le panier, réessayez.");
      }
    });
    return flushChainRef.current;
  }, [eventId]);

  // useCallback avec une identite stable (ne depend que de eventId, qui ne
  // change jamais pour une page donnee) : sans ca, PhotoGrid recevait une
  // nouvelle fonction a chaque frappe, ce qui invalidait le memo() de chaque
  // vignette et forcait react-window a tout re-rendre visuellement a chaque
  // clic (l'effet de "rechargement" signale).
  const handleToggleSelect = useCallback((photo: Photo) => {
    const wasSelected = selectedIdsRef.current.has(photo.id);

    // Mise a jour optimiste : l'utilisateur voit le changement immediatement,
    // sans attendre la reponse reseau (c'est cette attente qui donnait
    // l'impression que la page "rechargeait" a chaque selection).
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (wasSelected) next.delete(photo.id);
      else next.add(photo.id);
      return next;
    });
    setCartCount((c) => Math.max(0, c + (wasSelected ? -1 : 1)));

    if (!wasSelected) {
      bumpCartIcon();
      pendingAddIdsRef.current.add(photo.id);
      if (flushTimerRef.current) clearTimeout(flushTimerRef.current);
      flushTimerRef.current = setTimeout(flushPendingAdds, FLUSH_DEBOUNCE_MS);
      return;
    }

    // Deselection. Si l'ajout n'a pas encore ete envoye (toujours dans le
    // lot en attente), l'annuler localement suffit : aucune requete n'a
    // jamais ete faite pour cette photo.
    if (pendingAddIdsRef.current.has(photo.id)) {
      pendingAddIdsRef.current.delete(photo.id);
      return;
    }

    const itemId = itemIdByPhotoRef.current[photo.id];
    const removePromise = (async () => {
      try {
        if (itemId) {
          await api.removeCartItem(itemId);
        } else {
          // Cas rare : l'ajout de cette photo est dans un flush groupe deja
          // parti mais pas encore revenu (pas encore d'itemId connu). On
          // attend ce flush avant de pouvoir supprimer l'article qu'il va creer.
          await flushChainRef.current;
          const resolvedId = itemIdByPhotoRef.current[photo.id];
          if (resolvedId) await api.removeCartItem(resolvedId);
        }
        setItemIdByPhoto((prev) => {
          const next = { ...prev };
          delete next[photo.id];
          return next;
        });
      } catch {
        setSelectedIds((prev) => new Set(prev).add(photo.id));
        setCartCount((c) => c + 1);
        setError("Impossible de mettre à jour le panier, réessayez.");
      }
    })();
    pendingRemovesRef.current.push(removePromise);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventId, flushPendingAdds]);

  // "Tout selectionner" (ex: tous les resultats d'un cluster de visages) :
  // ajoute au lot en attente puis force un flush immediat (pas de raison
  // d'attendre le debounce pour une action deja volontairement groupee).
  const handleBulkAdd = useCallback((photos: Photo[]) => {
    const newPhotos = photos.filter((p) => !selectedIdsRef.current.has(p.id));
    if (newPhotos.length === 0) return;

    setSelectedIds((prev) => {
      const next = new Set(prev);
      newPhotos.forEach((p) => next.add(p.id));
      return next;
    });
    setCartCount((c) => c + newPhotos.length);
    bumpCartIcon();

    newPhotos.forEach((p) => pendingAddIdsRef.current.add(p.id));
    flushPendingAdds();
  }, [flushPendingAdds]);

  // En cas de selection rapide de plusieurs photos, naviguer vers le panier
  // avant que le lot en attente (et les suppressions en cours) n'aient
  // reellement ete confirmes cote serveur faisait atterrir sur un panier
  // incomplet (corrige seulement au rafraichissement, une fois tout arrive
  // en arriere-plan), on force donc un flush immediat et on attend tout ce
  // qui est encore en vol avant de naviguer.
  const [goingToCart, setGoingToCart] = useState(false);
  async function goToCart() {
    setGoingToCart(true);
    try {
      await Promise.all([flushPendingAdds(), ...pendingRemovesRef.current]);
    } finally {
      router.push(`/event/${eventId}/cart`);
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <main className="flex min-h-screen flex-col bg-surface">
      <header className="glass-strong sticky top-0 z-20 flex items-center justify-between px-4 py-3.5">
        <button
          type="button"
          onClick={() => router.push(`/event/${eventId}`)}
          className="flex items-center gap-1 text-sm font-medium text-ink-500 transition hover:text-brand"
        >
          &larr; Retour
        </button>
        <h1 className="text-sm font-semibold text-ink-900">
          Galerie <span className="text-ink-500">&middot; {total} photos</span>
        </h1>
        <button
          ref={cartIconRef}
          type="button"
          disabled={goingToCart}
          onClick={() => cartCount > 0 && goToCart()}
          className={`relative flex h-9 w-9 items-center justify-center rounded-full transition-all duration-200 disabled:opacity-60 ${
            cartCount > 0 ? "bg-brand text-white" : "bg-surface-alt text-ink-500"
          }`}
          aria-label="Panier"
        >
          <CartIcon />
          {cartCount > 0 && (
            <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-brand-accent text-[10px] font-bold text-brand">
              {cartCount}
            </span>
          )}
        </button>
      </header>

      <div className="glass flex items-center justify-center gap-2.5 px-4 py-2.5">
        <button
          type="button"
          onClick={() => setScanOpen(true)}
          className="flex items-center gap-1.5 rounded-full bg-brand px-4 py-2 text-xs font-semibold text-white transition hover:bg-brand-light"
        >
          <CameraIcon /> Scanner mon visage
        </button>
        <button
          type="button"
          onClick={() => setFindFacesOpen(true)}
          className="flex items-center gap-1.5 rounded-full border border-brand/20 bg-white/70 px-4 py-2 text-xs font-semibold text-brand transition hover:bg-white"
        >
          <UsersIcon /> Trouver mon visage
        </button>
      </div>

      {error && <p className="p-4 text-center text-red-600">{error}</p>}

      {loading && photos.length === 0 ? (
        <div className="grid flex-1 grid-cols-3 gap-1.5 p-1.5 sm:grid-cols-5">
          {Array.from({ length: 20 }).map((_, i) => (
            <div
              key={i}
              className="skeleton aspect-square animate-cell-in rounded-xl"
              style={{ animationDelay: `${(i % 6) * 45}ms` }}
            />
          ))}
        </div>
      ) : (
        <div key={page} className="flex-1 animate-fade-in pb-24">
          <PhotoGrid
            photos={photos}
            onPhotoOpen={setLightboxIndex}
            onToggleSelect={handleToggleSelect}
            selectedPhotoIds={selectedIds}
            bottomOffset={totalPages > 1 ? (cartCount > 0 ? 220 : 150) : 160}
          />
        </div>
      )}

      {totalPages > 1 && (
        <div
          className={`glass-strong fixed left-1/2 z-20 flex w-fit max-w-[94vw] -translate-x-1/2 justify-center rounded-full px-3 py-2 shadow-elevated transition-all duration-300 ${
            cartCount > 0 ? "bottom-24" : "bottom-4"
          }`}
        >
          <Pagination
            currentPage={page}
            totalPages={totalPages}
            disabled={loading}
            onPageChange={loadPage}
          />
        </div>
      )}

      {cartCount > 0 && (
        <button
          type="button"
          disabled={goingToCart}
          onClick={goToCart}
          className="glass-strong fixed inset-x-4 bottom-4 z-30 flex items-center justify-between rounded-2xl bg-brand/95 px-5 py-4 text-white shadow-elevated transition-transform duration-200 hover:scale-[1.01] active:scale-[0.99] animate-fade-in disabled:opacity-70 sm:inset-x-auto sm:right-6 sm:w-96"
        >
          <span className="font-semibold">{cartCount} photo{cartCount > 1 ? "s" : ""} sélectionnée{cartCount > 1 ? "s" : ""}</span>
          <span className="flex items-center gap-1 text-brand-accent">
            {goingToCart ? "Enregistrement..." : "Voir le panier"}{" "}
            {!goingToCart && <span aria-hidden>&rarr;</span>}
          </span>
        </button>
      )}

      {lightboxIndex !== null && (
        <PhotoLightbox
          photos={photos}
          index={lightboxIndex}
          onClose={() => setLightboxIndex(null)}
          onNavigate={setLightboxIndex}
          selectedPhotoIds={selectedIds}
          onToggleSelect={handleToggleSelect}
          frameCaption={frameCaption}
        />
      )}

      <ScanDialog
        eventId={eventId}
        open={scanOpen}
        onClose={() => {
          setScanOpen(false);
          scheduleCartReload();
        }}
        onCartChanged={scheduleCartReload}
      />
      <FindFacesDialog
        eventId={eventId}
        open={findFacesOpen}
        onClose={() => setFindFacesOpen(false)}
        selectedPhotoIds={selectedIds}
        onToggleSelect={handleToggleSelect}
        onBulkSelect={handleBulkAdd}
      />
    </main>
  );
}
