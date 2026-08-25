"use client";

import { AnimatePresence, motion, PanInfo, useMotionValue } from "framer-motion";
import { useCallback, useEffect, useRef, useState } from "react";
import { CheckIcon } from "@/components/icons";
import { flyToCart } from "@/lib/fly-to-cart";
import type { Photo } from "@/types/api";

interface PhotoLightboxProps {
  photos: Photo[];
  index: number;
  onClose: () => void;
  onNavigate: (index: number) => void;
  selectedPhotoIds: Set<string>;
  onToggleSelect: (photo: Photo) => void;
  addingPhotoId?: string | null;
  showCartAction?: boolean;
}

const SWIPE_THRESHOLD = 60;
const SWIPE_VELOCITY_THRESHOLD = 500;
const MAX_ZOOM = 4;

function distanceBetween(t1: React.Touch, t2: React.Touch) {
  return Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY);
}

export default function PhotoLightbox({
  photos,
  index,
  onClose,
  onNavigate,
  selectedPhotoIds,
  onToggleSelect,
  addingPhotoId,
  showCartAction = true,
}: PhotoLightboxProps) {
  const photo = photos[index];
  const hasPrev = index > 0;
  const hasNext = index < photos.length - 1;
  const [direction, setDirection] = useState(1);

  const imageWrapRef = useRef<HTMLDivElement>(null);
  const scale = useMotionValue(1);
  const panX = useMotionValue(0);
  const panY = useMotionValue(0);
  const pinchRef = useRef<{ startDist: number; startScale: number } | null>(null);
  const [isZoomed, setIsZoomed] = useState(false);

  // Chargement progressif : la miniature (deja en cache depuis la grille)
  // s'affiche immediatement, sans aucune attente visible. La version
  // "preview" (plus grande, plus nette) charge silencieusement par-dessus
  // en arriere-plan et prend le relais en fondu des qu'elle est prete —
  // aucun spinner, aucune latence percue, juste une nettete qui s'ameliore.
  const [previewLoaded, setPreviewLoaded] = useState(false);

  const resetZoom = useCallback(() => {
    scale.set(1);
    panX.set(0);
    panY.set(0);
    setIsZoomed(false);
  }, [scale, panX, panY]);

  const goPrev = useCallback(() => {
    if (hasPrev) {
      setDirection(-1);
      resetZoom();
      onNavigate(index - 1);
    }
  }, [hasPrev, index, onNavigate, resetZoom]);

  const goNext = useCallback(() => {
    if (hasNext) {
      setDirection(1);
      resetZoom();
      onNavigate(index + 1);
    }
  }, [hasNext, index, onNavigate, resetZoom]);

  useEffect(() => {
    setPreviewLoaded(false);
    if (!photo || photo.preview_url === photo.thumbnail_url) return;
    const img = new window.Image();
    img.src = photo.preview_url;
    if (img.complete) {
      setPreviewLoaded(true);
      return;
    }
    img.onload = () => setPreviewLoaded(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [photo?.id]);

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft") goPrev();
      if (e.key === "ArrowRight") goNext();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose, goPrev, goNext]);

  // Pincer-zoomer a deux doigts (ecran tactile). En dessous de 2 doigts on
  // laisse le geste "drag" de framer-motion gerer le swipe navigation.
  function handleTouchStart(e: React.TouchEvent) {
    if (e.touches.length === 2) {
      pinchRef.current = {
        startDist: distanceBetween(e.touches[0], e.touches[1]),
        startScale: scale.get(),
      };
    }
  }

  function handleTouchMove(e: React.TouchEvent) {
    if (e.touches.length === 2 && pinchRef.current) {
      e.preventDefault();
      const dist = distanceBetween(e.touches[0], e.touches[1]);
      const nextScale = Math.min(
        MAX_ZOOM,
        Math.max(1, pinchRef.current.startScale * (dist / pinchRef.current.startDist))
      );
      scale.set(nextScale);
      setIsZoomed(nextScale > 1.02);
    }
  }

  function handleTouchEnd(e: React.TouchEvent) {
    if (e.touches.length < 2) {
      pinchRef.current = null;
      if (scale.get() <= 1.02) resetZoom();
    }
  }

  function handleDragEnd(_e: unknown, info: PanInfo) {
    if (isZoomed) return;
    const { offset, velocity } = info;
    if (offset.x < -SWIPE_THRESHOLD || velocity.x < -SWIPE_VELOCITY_THRESHOLD) {
      goNext();
    } else if (offset.x > SWIPE_THRESHOLD || velocity.x > SWIPE_VELOCITY_THRESHOLD) {
      goPrev();
    }
  }

  function handleAddToCart() {
    if (!isSelected) flyToCart(imageWrapRef.current);
    onToggleSelect(photo);
  }

  if (!photo) return null;

  const isSelected = selectedPhotoIds.has(photo.id);
  const isAdding = addingPhotoId === photo.id;

  return (
    <div
      className="fixed inset-0 z-[60] flex flex-col overflow-hidden bg-brand/90 backdrop-blur-md animate-fade-in"
      onClick={onClose}
    >
      {/* barre haute */}
      <div className="relative z-20 flex items-center justify-between p-4">
        <span className="glass-pill px-3.5 py-1.5 text-xs font-medium text-white">
          {index + 1} / {photos.length}
        </span>
        <button
          type="button"
          onClick={onClose}
          className="glass-pill flex h-10 w-10 items-center justify-center text-lg text-white transition hover:bg-white/20"
          aria-label="Fermer"
        >
          &times;
        </button>
      </div>

      {/* image + nav */}
      <div
        className="relative flex flex-1 touch-none items-center justify-center overflow-hidden px-4"
        onClick={(e) => e.stopPropagation()}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        {hasPrev && (
          <button
            type="button"
            onClick={goPrev}
            className="glass-pill absolute left-3 top-1/2 z-10 flex h-11 w-11 -translate-y-1/2 items-center justify-center text-xl text-white transition hover:bg-white/20 sm:left-6"
            aria-label="Photo precedente"
          >
            &larr;
          </button>
        )}

        <AnimatePresence initial={false} custom={direction} mode="popLayout">
          <motion.div
            key={photo.id}
            ref={imageWrapRef}
            custom={direction}
            variants={{
              enter: (dir: number) => ({ x: dir > 0 ? 80 : -80, opacity: 0 }),
              center: { x: 0, opacity: 1 },
              exit: (dir: number) => ({ x: dir > 0 ? -80 : 80, opacity: 0 }),
            }}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ type: "spring", stiffness: 320, damping: 32 }}
            drag={isZoomed ? false : "x"}
            dragElastic={0.15}
            dragConstraints={{ left: 0, right: 0 }}
            onDragEnd={handleDragEnd}
            className="flex max-h-[70vh] max-w-full items-center justify-center"
          >
            <motion.div
              onDoubleClick={resetZoom}
              style={{ scale, x: panX, y: panY }}
              className="relative flex max-h-[70vh] max-w-full items-center justify-center"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={photo.thumbnail_url}
                alt={photo.original_filename}
                className="max-h-[70vh] max-w-full select-none rounded-2xl object-contain shadow-elevated"
                draggable={false}
              />
              {photo.preview_url !== photo.thumbnail_url && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={photo.preview_url}
                  alt={photo.original_filename}
                  className={`absolute inset-0 h-full w-full select-none rounded-2xl object-contain shadow-elevated transition-opacity duration-300 ${
                    previewLoaded ? "opacity-100" : "opacity-0"
                  }`}
                  draggable={false}
                />
              )}
            </motion.div>
          </motion.div>
        </AnimatePresence>

        {hasNext && (
          <button
            type="button"
            onClick={goNext}
            className="glass-pill absolute right-3 top-1/2 z-10 flex h-11 w-11 -translate-y-1/2 items-center justify-center text-xl text-white transition hover:bg-white/20 sm:right-6"
            aria-label="Photo suivante"
          >
            &rarr;
          </button>
        )}
      </div>

      {/* barre basse */}
      <div className="relative z-20 flex flex-col items-center gap-3 p-5" onClick={(e) => e.stopPropagation()}>
        <p className="max-w-[80vw] truncate text-xs text-white/70">{photo.original_filename}</p>
        {showCartAction && (
          <button
            type="button"
            disabled={isAdding}
            onClick={handleAddToCart}
            className={`glass-strong flex items-center gap-2 rounded-full px-6 py-3 font-semibold transition-all duration-200 active:scale-95 disabled:opacity-60 ${
              isSelected ? "!bg-brand-accent/90 !text-brand" : "text-brand"
            }`}
          >
            {isSelected ? (
              <>
                <CheckIcon /> Ajoute au panier
              </>
            ) : (
              <>{isAdding ? "Ajout..." : "Ajouter au panier"}</>
            )}
          </button>
        )}
      </div>
    </div>
  );
}
