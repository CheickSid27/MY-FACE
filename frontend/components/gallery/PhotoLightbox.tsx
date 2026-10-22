"use client";

import { AnimatePresence, motion, PanInfo, useMotionValue } from "framer-motion";
// Zoom : pincer a deux doigts, double toucher (ou double clic), molette ; la
// photo zoomee se deplace au doigt ou a la souris.
import { useCallback, useEffect, useRef, useState } from "react";
import { CheckIcon } from "@/components/icons";
import { flyToCart } from "@/lib/fly-to-cart";
import FramedPhoto from "@/components/photo/FramedPhoto";
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
  /** Voir Event.frame_caption : absent/vide = pas de cadre decoratif. */
  frameCaption?: string | null;
}

const SWIPE_THRESHOLD = 60;
const SWIPE_VELOCITY_THRESHOLD = 500;
const MAX_ZOOM = 5;
const DOUBLE_TAP_ZOOM = 2.5;
const DOUBLE_TAP_MS = 300;
const TAP_MOVE_PX = 12;

type Point = { x: number; y: number };

function distance(a: Point, b: Point) {
  return Math.hypot(b.x - a.x, b.y - a.y);
}

function middle(a: Point, b: Point): Point {
  return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
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
  frameCaption,
}: PhotoLightboxProps) {
  const photo = photos[index];
  const hasPrev = index > 0;
  const hasNext = index < photos.length - 1;
  const [direction, setDirection] = useState(1);

  const imageWrapRef = useRef<HTMLDivElement>(null);
  const zoomRef = useRef<HTMLDivElement>(null);
  const areaRef = useRef<HTMLDivElement>(null);
  const scale = useMotionValue(1);
  const panX = useMotionValue(0);
  const panY = useMotionValue(0);
  const [isZoomed, setIsZoomed] = useState(false);
  // Gestes du zoom (doigts, souris) : pointeurs en cours, pincement, double toucher.
  const pointers = useRef(new Map<number, Point>());
  const pinch = useRef<{ dist: number; mid: Point } | null>(null);
  const tapStart = useRef<{ x: number; y: number; time: number } | null>(null);
  const lastTap = useRef<{ x: number; y: number; time: number } | null>(null);

  // Chargement progressif : la miniature (deja en cache depuis la grille)
  // s'affiche immediatement, sans aucune attente visible. La version
  // "preview" (plus grande, plus nette) charge silencieusement par-dessus
  // en arriere-plan et prend le relais en fondu des qu'elle est prete
  // aucun spinner, aucune latence percue, juste une nettete qui s'ameliore.
  const [previewLoaded, setPreviewLoaded] = useState(false);

  const resetZoom = useCallback(() => {
    scale.set(1);
    panX.set(0);
    panY.set(0);
    setIsZoomed(false);
  }, [scale, panX, panY]);

  // Deplacement de la photo zoomee, sans jamais laisser apparaitre de vide
  // au-dela de ses bords.
  const setPan = useCallback(
    (x: number, y: number, s: number) => {
      const el = zoomRef.current;
      const maxX = el ? ((s - 1) * el.offsetWidth) / 2 : 0;
      const maxY = el ? ((s - 1) * el.offsetHeight) / 2 : 0;
      panX.set(Math.max(-maxX, Math.min(maxX, x)));
      panY.set(Math.max(-maxY, Math.min(maxY, y)));
    },
    [panX, panY]
  );

  // Zoom autour d'un point de l'ecran (doigts, endroit touche, souris) : ce
  // point de la photo reste sous le doigt pendant le zoom.
  const zoomAt = useCallback(
    (nextScale: number, focus: Point) => {
      const current = scale.get();
      const s = Math.min(MAX_ZOOM, Math.max(1, nextScale));
      if (s <= 1.01) {
        resetZoom();
        return;
      }
      // Repere : le cadre non zoome de la photo (le parent de l'element qui
      // zoome ; la ref de l'animation d'entree n'est pas fiable ici).
      const rect = zoomRef.current?.parentElement?.getBoundingClientRect();
      const cx = rect ? rect.left + rect.width / 2 : focus.x;
      const cy = rect ? rect.top + rect.height / 2 : focus.y;
      const k = s / current;
      scale.set(s);
      setPan((focus.x - cx) * (1 - k) + k * panX.get(), (focus.y - cy) * (1 - k) + k * panY.get(), s);
      setIsZoomed(true);
    },
    [scale, panX, panY, setPan, resetZoom]
  );
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

  useEffect(() => {
    resetZoom();
  }, [photo?.id, resetZoom]);

  // Molette (ordinateur) : zoom sur l'endroit vise. Ecouteur natif non
  // passif, sinon la page derriere la visionneuse defilerait.
  useEffect(() => {
    const area = areaRef.current;
    if (!area) return;
    function onWheel(e: WheelEvent) {
      e.preventDefault();
      zoomAt(scale.get() * Math.exp(-e.deltaY * 0.0015), { x: e.clientX, y: e.clientY });
    }
    area.addEventListener("wheel", onWheel, { passive: false });
    return () => area.removeEventListener("wheel", onWheel);
  }, [zoomAt, scale]);

  // Gestes : deux doigts = pincer pour zoomer (et deplacer) ; un doigt ou la
  // souris sur une photo zoomee = la deplacer ; double toucher ou double clic =
  // zoomer sur l'endroit touche, ou revenir a la taille normale. Sans zoom, un
  // doigt fait defiler les photos (glisser de framer-motion).
  function handlePointerDown(e: React.PointerEvent) {
    if ((e.target as HTMLElement).closest("button")) return;
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pointers.current.size === 1) {
      tapStart.current = { x: e.clientX, y: e.clientY, time: Date.now() };
    } else if (pointers.current.size === 2) {
      const [a, b] = Array.from(pointers.current.values());
      pinch.current = { dist: distance(a, b), mid: middle(a, b) };
      tapStart.current = null;
      setIsZoomed(true); // coupe le glisser de navigation pendant le pincement
    }
  }

  function handlePointerMove(e: React.PointerEvent) {
    const previous = pointers.current.get(e.pointerId);
    if (!previous) return;
    const point = { x: e.clientX, y: e.clientY };
    pointers.current.set(e.pointerId, point);
    if (pointers.current.size >= 2 && pinch.current) {
      const [a, b] = Array.from(pointers.current.values());
      const dist = distance(a, b);
      const mid = middle(a, b);
      const s = scale.get();
      zoomAt(s * (dist / pinch.current.dist), mid);
      setIsZoomed(true); // reste bloque tant que les deux doigts sont poses
      const now = scale.get();
      setPan(panX.get() + mid.x - pinch.current.mid.x, panY.get() + mid.y - pinch.current.mid.y, now);
      pinch.current = { dist, mid };
    } else if (pointers.current.size === 1 && scale.get() > 1.01) {
      setPan(panX.get() + point.x - previous.x, panY.get() + point.y - previous.y, scale.get());
    }
  }

  function handlePointerUp(e: React.PointerEvent) {
    if (!pointers.current.has(e.pointerId)) return;
    pointers.current.delete(e.pointerId);
    if (pointers.current.size < 2) pinch.current = null;
    if (pointers.current.size === 0 && scale.get() <= 1.01) resetZoom();

    const start = tapStart.current;
    tapStart.current = null;
    if (!start || e.type === "pointercancel") return;
    const now = Date.now();
    const isTap = now - start.time < 350 && Math.hypot(e.clientX - start.x, e.clientY - start.y) < TAP_MOVE_PX;
    if (!isTap) return;
    const last = lastTap.current;
    if (last && now - last.time < DOUBLE_TAP_MS && Math.hypot(e.clientX - last.x, e.clientY - last.y) < 40) {
      lastTap.current = null;
      if (scale.get() > 1.01) resetZoom();
      else zoomAt(DOUBLE_TAP_ZOOM, { x: e.clientX, y: e.clientY });
    } else {
      lastTap.current = { x: e.clientX, y: e.clientY, time: now };
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
        ref={areaRef}
        className={`relative flex flex-1 touch-none items-center justify-center overflow-hidden px-4 ${
          isZoomed ? "cursor-grab active:cursor-grabbing" : ""
        }`}
        onClick={(e) => e.stopPropagation()}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
      >
        {hasPrev && (
          <button
            type="button"
            onClick={goPrev}
            className="glass-pill absolute left-3 top-1/2 z-10 flex h-11 w-11 -translate-y-1/2 items-center justify-center text-xl text-white transition hover:bg-white/20 sm:left-6"
            aria-label="Photo précédente"
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
              ref={zoomRef}
              style={{ scale, x: panX, y: panY }}
              className="relative flex max-h-[70vh] max-w-full items-center justify-center"
            >
              <FramedPhoto caption={frameCaption}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={photo.thumbnail_url}
                  alt={photo.original_filename}
                  className={`max-h-[70vh] max-w-full select-none object-contain ${frameCaption ? "" : "rounded-2xl shadow-elevated"}`}
                  draggable={false}
                />
                {photo.preview_url !== photo.thumbnail_url && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={photo.preview_url}
                    alt={photo.original_filename}
                    className={`absolute inset-0 h-full w-full select-none object-contain transition-opacity duration-300 ${frameCaption ? "" : "rounded-2xl shadow-elevated"} ${
                      previewLoaded ? "opacity-100" : "opacity-0"
                    }`}
                    draggable={false}
                  />
                )}
              </FramedPhoto>
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
