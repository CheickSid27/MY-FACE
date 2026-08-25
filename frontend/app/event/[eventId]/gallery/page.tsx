"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import FindFacesDialog from "@/components/faces/FindFacesDialog";
import PhotoGrid from "@/components/gallery/PhotoGrid";
import PhotoLightbox from "@/components/gallery/PhotoLightbox";
import { CameraIcon, CartIcon, UsersIcon } from "@/components/icons";
import ScanDialog from "@/components/scan/ScanDialog";
import { api } from "@/lib/api-client";
import { getCartSessionId, setCartSessionId } from "@/lib/cart";
import type { CartRead, Photo } from "@/types/api";

const PAGE_SIZE = 60;

export default function GalleryPage() {
  const { eventId } = useParams<{ eventId: string }>();
  const router = useRouter();
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  const loadPage = useCallback(
    async (pageToLoad: number) => {
      setLoading(true);
      try {
        const data = await api.listPhotos(eventId, pageToLoad, PAGE_SIZE);
        setPhotos((prev) => (pageToLoad === 1 ? data.items : [...prev, ...data.items]));
        setTotal(data.total);
        setPage(pageToLoad);
      } catch {
        setError("Impossible de charger la galerie.");
      } finally {
        setLoading(false);
      }
    },
    [eventId]
  );

  useEffect(() => {
    loadPage(1);
  }, [loadPage]);

  function syncCart(cart: CartRead) {
    setSelectedIds(new Set(cart.items.map((item) => item.photo.id)));
    setCartCount(cart.items.length);
    const map: Record<string, string> = {};
    cart.items.forEach((item) => {
      map[item.photo.id] = item.id;
    });
    setItemIdByPhoto(map);
  }

  useEffect(() => {
    const sessionId = getCartSessionId(eventId);
    if (!sessionId) return;
    api
      .getCart(sessionId)
      .then(syncCart)
      .catch(() => {
        // panier expire ou introuvable : on repart d'un panier vide
      });
  }, [eventId]);

  // File d'attente serialisee pour les appels reseau du panier : l'UI doit
  // rester instantanee (mise a jour optimiste immediate) meme si l'utilisateur
  // selectionne plusieurs photos tres vite d'affilee, mais les requetes elles
  // memes doivent partir dans l'ordre et une par une, car la toute premiere
  // cree la session panier cote serveur (session_id) que les suivantes
  // doivent reutiliser (deux "add" concurrents sans session_id creeraient
  // chacun leur propre panier au lieu de partager le meme).
  const queueRef = useRef<Promise<void>>(Promise.resolve());
  const itemIdByPhotoRef = useRef<Record<string, string>>({});
  itemIdByPhotoRef.current = itemIdByPhoto;
  const selectedIdsRef = useRef<Set<string>>(selectedIds);
  selectedIdsRef.current = selectedIds;

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
    if (!wasSelected) bumpCartIcon();

    queueRef.current = queueRef.current.then(async () => {
      try {
        if (wasSelected) {
          const itemId = itemIdByPhotoRef.current[photo.id];
          if (itemId) {
            await api.removeCartItem(itemId);
            setItemIdByPhoto((prev) => {
              const next = { ...prev };
              delete next[photo.id];
              return next;
            });
          }
        } else {
          const sessionId = getCartSessionId(eventId);
          const cart = await api.addToCart(eventId, photo.id, sessionId);
          setCartSessionId(eventId, cart.session_id);
          syncCart(cart);
        }
      } catch {
        // echec reseau : on annule la mise a jour optimiste pour cette photo
        setSelectedIds((prev) => {
          const next = new Set(prev);
          if (wasSelected) next.add(photo.id);
          else next.delete(photo.id);
          return next;
        });
        setCartCount((c) => Math.max(0, c + (wasSelected ? 1 : -1)));
        setError("Impossible de mettre a jour le panier, reessayez.");
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventId]);

  const hasMore = photos.length < total;

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
          onClick={() => cartCount > 0 && router.push(`/event/${eventId}/cart`)}
          className={`relative flex h-9 w-9 items-center justify-center rounded-full transition-all duration-200 ${
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
        <div className="flex-1 pb-24">
          <PhotoGrid
            photos={photos}
            onPhotoOpen={setLightboxIndex}
            onToggleSelect={handleToggleSelect}
            selectedPhotoIds={selectedIds}
          />
        </div>
      )}

      {hasMore && (
        <div className="glass-strong flex justify-center p-3">
          <button
            type="button"
            disabled={loading}
            onClick={() => loadPage(page + 1)}
            className="btn-ghost !px-6 !py-2.5 text-sm"
          >
            {loading ? "Chargement..." : "Charger plus"}
          </button>
        </div>
      )}

      {cartCount > 0 && (
        <button
          type="button"
          onClick={() => router.push(`/event/${eventId}/cart`)}
          className="glass-strong fixed inset-x-4 bottom-4 z-30 flex items-center justify-between rounded-2xl bg-brand/95 px-5 py-4 text-white shadow-elevated transition-transform duration-200 hover:scale-[1.01] active:scale-[0.99] animate-fade-in sm:inset-x-auto sm:right-6 sm:w-96"
        >
          <span className="font-semibold">{cartCount} photo(s) selectionnee(s)</span>
          <span className="flex items-center gap-1 text-brand-accent">
            Voir le panier <span aria-hidden>&rarr;</span>
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
        />
      )}

      <ScanDialog eventId={eventId} open={scanOpen} onClose={() => setScanOpen(false)} />
      <FindFacesDialog
        eventId={eventId}
        open={findFacesOpen}
        onClose={() => setFindFacesOpen(false)}
        selectedPhotoIds={selectedIds}
        onToggleSelect={handleToggleSelect}
      />
    </main>
  );
}
