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
import { CART_ICON_ID } from "@/lib/fly-to-cart";
import type { Photo } from "@/types/api";

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
  const [cartCount, setCartCount] = useState(0);
  const [addingPhotoId, setAddingPhotoId] = useState<string | null>(null);
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);
  const [scanOpen, setScanOpen] = useState(false);
  const [findFacesOpen, setFindFacesOpen] = useState(false);
  const cartIconRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const el = cartIconRef.current;
    if (!el) return;
    function bump() {
      el!.classList.remove("animate-cart-bump");
      void el!.offsetWidth;
      el!.classList.add("animate-cart-bump");
    }
    el.addEventListener("cart-landed", bump);
    return () => el.removeEventListener("cart-landed", bump);
  }, []);

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

  useEffect(() => {
    const sessionId = getCartSessionId(eventId);
    if (!sessionId) return;
    api
      .getCart(sessionId)
      .then((cart) => {
        setSelectedIds(new Set(cart.items.map((item) => item.photo.id)));
        setCartCount(cart.items.length);
      })
      .catch(() => {
        // panier expire ou introuvable : on repart d'un panier vide
      });
  }, [eventId]);

  async function handleToggleSelect(photo: Photo) {
    if (selectedIds.has(photo.id) || addingPhotoId) return;
    setAddingPhotoId(photo.id);
    try {
      const sessionId = getCartSessionId(eventId);
      const cart = await api.addToCart(eventId, photo.id, sessionId);
      setCartSessionId(eventId, cart.session_id);
      setSelectedIds(new Set(cart.items.map((item) => item.photo.id)));
      setCartCount(cart.items.length);
    } catch {
      setError("Impossible d'ajouter la photo au panier.");
    } finally {
      setAddingPhotoId(null);
    }
  }

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
          id={CART_ICON_ID}
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
            addingPhotoId={addingPhotoId}
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
          addingPhotoId={addingPhotoId}
        />
      )}

      <ScanDialog eventId={eventId} open={scanOpen} onClose={() => setScanOpen(false)} />
      <FindFacesDialog
        eventId={eventId}
        open={findFacesOpen}
        onClose={() => setFindFacesOpen(false)}
        selectedPhotoIds={selectedIds}
        onToggleSelect={handleToggleSelect}
        addingPhotoId={addingPhotoId}
      />
    </main>
  );
}
