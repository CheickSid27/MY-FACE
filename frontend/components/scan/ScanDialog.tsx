"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import PhotoLightbox from "@/components/gallery/PhotoLightbox";
import { AlertIcon, CameraIcon, CheckIcon, SearchIcon } from "@/components/icons";
import { api, ApiError } from "@/lib/api-client";
import { getCartSessionId, setCartSessionId } from "@/lib/cart";
import { flyToCart } from "@/lib/fly-to-cart";
import { getKioskToken } from "@/lib/kiosk";
import type { CartRead, FaceScanMatch, Photo } from "@/types/api";

type Step = "consent" | "camera" | "scanning" | "results" | "error";

const SELFIE_MAX_SIDE = 800;
const SELFIE_JPEG_QUALITY = 0.85;

interface ScanDialogProps {
  eventId: string;
  open: boolean;
  onClose: () => void;
  /** Appele apres chaque ajout/retrait confirme par le serveur, pour que la
   * page parente (galerie) resynchronise son propre etat du panier. */
  onCartChanged?: () => void;
}

export default function ScanDialog({ eventId, open, onClose, onCartChanged }: ScanDialogProps) {
  const router = useRouter();

  const [step, setStep] = useState<Step>("consent");
  const [error, setError] = useState<string | null>(null);
  const [matches, setMatches] = useState<FaceScanMatch[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [itemIdByPhoto, setItemIdByPhoto] = useState<Record<string, string>>({});
  const [cartCount, setCartCount] = useState(0);
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);
  const [videoReady, setVideoReady] = useState(false);

  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }, []);

  useEffect(() => {
    if (!open) {
      stopCamera();
      setStep("consent");
      setMatches([]);
      setError(null);
    }
  }, [open, stopCamera]);

  useEffect(() => stopCamera, [stopCamera]);

  // Le <video> n'existe dans le DOM qu'une fois step==="camera" rendu par
  // React ; l'assigner juste apres setStep("camera") (avant le prochain
  // rendu) lit un videoRef encore null et le flux ne s'affiche jamais
  // (boite figee vide, meme si la camera est bien active). On attend donc
  // que le rendu ait reellement eu lieu via cet effet.
  useEffect(() => {
    if (step !== "camera" || !videoRef.current || !streamRef.current) return;
    const video = videoRef.current;
    setVideoReady(false);
    video.srcObject = streamRef.current;

    // videoWidth/videoHeight peuvent devenir non-nuls (metadonnees chargees)
    // avant qu'une vraie image decodee soit disponible : capturer a ce
    // moment-la donne une frame noire/vide, d'ou un selfie sans visage
    // detectable malgre un vrai visage devant la camera. "loadeddata"
    // garantit qu'au moins une frame reelle est decodee.
    function handleLoadedData() {
      setVideoReady(true);
    }
    video.addEventListener("loadeddata", handleLoadedData);

    video.play().catch(() => {
      // certains navigateurs bloquent l'autoplay tant que l'utilisateur n'a
      // pas interagi ; le flux reste correctement attache, play() sera
      // relance naturellement au premier tap si besoin.
    });

    return () => video.removeEventListener("loadeddata", handleLoadedData);
  }, [step]);

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
    if (!open) return;
    const sessionId = getCartSessionId(eventId);
    if (!sessionId) return;
    api
      .getCart(sessionId)
      .then(syncCart)
      .catch(() => {
        // panier expire ou introuvable
      });
  }, [open, eventId]);

  async function startCamera() {
    setError(null);

    if (typeof window !== "undefined" && !window.isSecureContext) {
      setError(
        "L'acces a la camera necessite une connexion securisee (https://). Ouvrez ce lien en HTTPS, pas en http://."
      );
      setStep("error");
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      setError("Votre navigateur ne supporte pas l'acces a la camera. Essayez avec Chrome ou Safari a jour.");
      setStep("error");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } });
      streamRef.current = stream;
      setStep("camera");
    } catch (err) {
      const name = err instanceof DOMException ? err.name : "";
      if (name === "NotAllowedError" || name === "PermissionDeniedError") {
        setError(
          "Acces a la camera refuse. Autorisez la camera pour ce site dans les reglages de votre navigateur, puis reessayez."
        );
      } else if (name === "NotFoundError" || name === "DevicesNotFoundError") {
        setError("Aucune camera detectee sur cet appareil.");
      } else if (name === "NotReadableError") {
        setError("La camera est deja utilisee par une autre application. Fermez-la et reessayez.");
      } else {
        setError("Impossible d'acceder a la camera. Verifiez les autorisations de votre navigateur.");
      }
      setStep("error");
    }
  }

  async function capture() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    if (!videoReady || !video.videoWidth || !video.videoHeight) {
      // Capturer avant qu'une vraie frame soit decodee (meme si les
      // dimensions existent deja) donne une image noire/vide -> "aucun
      // visage detecte" alors qu'un visage est pourtant bien devant la
      // camera. On bloque plutot que d'echouer silencieusement.
      setError("La camera n'est pas encore prete, patientez une seconde puis reessayez.");
      return;
    }

    // Selfie reduit a SELFIE_MAX_SIDE avant envoi : la detection travaille en
    // 640 px (InsightFace det_size) et le visage d'un selfie occupe une
    // grande partie de l'image, donc aucune perte de precision. Via le tunnel,
    // l'envoi passe par la connexion Internet du PC de l'evenement : un
    // selfie pleine resolution (1080p) mettait 10 a 20 s a arriver, contre
    // quelques secondes une fois reduit (resultats identiques, mesure).
    const scale = Math.min(1, SELFIE_MAX_SIDE / Math.max(video.videoWidth, video.videoHeight));
    canvas.width = Math.round(video.videoWidth * scale);
    canvas.height = Math.round(video.videoHeight * scale);
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    const blob: Blob | null = await new Promise((resolve) =>
      canvas.toBlob(resolve, "image/jpeg", SELFIE_JPEG_QUALITY)
    );
    if (!blob) return;

    stopCamera();
    setStep("scanning");

    try {
      const result = await api.scanFace(eventId, blob, true, getKioskToken(eventId));
      setMatches(result.matches);
      setStep("results");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors du scan.");
      setStep("error");
    }
  }

  const itemIdByPhotoRef = useRef<Record<string, string>>({});
  itemIdByPhotoRef.current = itemIdByPhoto;

  // Meme principe complet (et meme explication) que
  // app/event/[eventId]/gallery/page.tsx : ajouts groupes en un seul appel
  // /cart/add-bulk apres un court debounce (ou immediatement au moment
  // d'aller au panier) plutot qu'une requete reseau sequentielle par photo
  // selectionnee.
  const FLUSH_DEBOUNCE_MS = 500;
  const pendingAddIdsRef = useRef<Set<string>>(new Set());
  const flushTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const flushChainRef = useRef<Promise<void>>(Promise.resolve());
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
        onCartChanged?.();
      } catch {
        setSelectedIds((prev) => {
          const next = new Set(prev);
          ids.forEach((id) => next.delete(id));
          return next;
        });
        setCartCount((c) => Math.max(0, c - ids.length));
        setError("Impossible de mettre a jour le panier, reessayez.");
      }
    });
    return flushChainRef.current;
  }, [eventId, onCartChanged]);

  function handlePhotoClick(photo: Photo) {
    const wasSelected = selectedIds.has(photo.id);

    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (wasSelected) next.delete(photo.id);
      else next.add(photo.id);
      return next;
    });
    setCartCount((c) => Math.max(0, c + (wasSelected ? -1 : 1)));

    if (!wasSelected) {
      pendingAddIdsRef.current.add(photo.id);
      if (flushTimerRef.current) clearTimeout(flushTimerRef.current);
      flushTimerRef.current = setTimeout(flushPendingAdds, FLUSH_DEBOUNCE_MS);
      return;
    }

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
          await flushChainRef.current;
          const resolvedId = itemIdByPhotoRef.current[photo.id];
          if (resolvedId) await api.removeCartItem(resolvedId);
        }
        setItemIdByPhoto((prev) => {
          const next = { ...prev };
          delete next[photo.id];
          return next;
        });
        onCartChanged?.();
      } catch {
        setSelectedIds((prev) => new Set(prev).add(photo.id));
        setCartCount((c) => c + 1);
        setError("Impossible de mettre a jour le panier, reessayez.");
      }
    })();
    pendingRemovesRef.current.push(removePromise);
  }

  // Voir le meme correctif (et son explication complete) dans
  // app/event/[eventId]/gallery/page.tsx : naviguer vers le panier avant que
  // le lot en attente et les suppressions en cours n'aient ete confirmes
  // faisait atterrir sur un panier incomplet.
  const [goingToCart, setGoingToCart] = useState(false);
  async function goToCart() {
    setGoingToCart(true);
    try {
      await Promise.all([flushPendingAdds(), ...pendingRemovesRef.current]);
    } finally {
      onClose();
      router.push(`/event/${eventId}/cart`);
    }
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-brand/70 p-4 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="glass-strong relative flex max-h-[92vh] w-full max-w-lg flex-col overflow-hidden rounded-2xl shadow-elevated animate-scale-in sm:max-w-xl"
      >
        <button
          type="button"
          onClick={onClose}
          className="glass-pill absolute right-4 top-4 z-10 flex h-9 w-9 items-center justify-center text-white transition hover:bg-white/20"
          aria-label="Fermer"
        >
          &times;
        </button>

        {step === "consent" && (
          <div className="flex flex-col gap-6 bg-gradient-to-br from-brand to-brand-light p-8 text-white">
            <div>
              <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-brand-accent/20 text-2xl text-brand-accent">
                <CameraIcon />
              </div>
              <h2 className="text-xl font-bold">Scanner mon visage</h2>
            </div>
            <p className="text-sm leading-relaxed text-ink-300">
              Pour retrouver vos photos, votre selfie est envoye de facon securisee a notre
              serveur, qui le compare aux visages des photos de l&apos;evenement. Il n&apos;est
              jamais enregistre : il est efface des la fin de la recherche.
            </p>
            <p className="text-sm leading-relaxed text-ink-300">
              Ce scan est facultatif : vous pouvez aussi parcourir la galerie. Pour faire
              retirer vos photos ou vos donnees, ecrivez a contact@myfaceci.online.
            </p>
            <div className="flex flex-col gap-3 sm:flex-row">
              <button type="button" onClick={startCamera} className="btn-accent flex-1">
                J&apos;accepte et je continue
              </button>
              <button type="button" onClick={onClose} className="btn-ghost flex-1 !bg-white/5 !text-white">
                Annuler
              </button>
            </div>
          </div>
        )}

        {step === "camera" && (
          <div className="flex flex-col items-center gap-5 bg-gradient-to-br from-black to-brand p-6">
            <div className="glass-dark relative w-full overflow-hidden rounded-xl p-1.5">
              <div className="relative overflow-hidden rounded-lg">
                <video
                  ref={videoRef}
                  playsInline
                  muted
                  className="max-h-[60vh] w-full -scale-x-100 rounded-lg object-cover"
                />
                {/* Reticule + balayage laser façon scanner futuriste, purement
                    visuel : la frame capturee (ctx.drawImage) reste la vraie
                    orientation camera, non retournee, pour la reconnaissance. */}
                {videoReady && (
                  <div className="pointer-events-none absolute inset-0">
                    <div className="absolute inset-6 rounded-lg border border-brand-accent/30" />
                    <span className="absolute left-4 top-4 h-6 w-6 border-l-2 border-t-2 border-brand-accent animate-scan-pulse" />
                    <span className="absolute right-4 top-4 h-6 w-6 border-r-2 border-t-2 border-brand-accent animate-scan-pulse" />
                    <span className="absolute bottom-4 left-4 h-6 w-6 border-b-2 border-l-2 border-brand-accent animate-scan-pulse" />
                    <span className="absolute bottom-4 right-4 h-6 w-6 border-b-2 border-r-2 border-brand-accent animate-scan-pulse" />
                    <div className="absolute left-0 right-0 h-0.5 bg-brand-accent shadow-[0_0_12px_2px_rgba(255,255,255,0.7)] animate-scan-line" />
                  </div>
                )}
              </div>
            </div>
            <canvas ref={canvasRef} className="hidden" />
            <button
              type="button"
              onClick={capture}
              disabled={!videoReady}
              className="btn-accent w-full max-w-xs disabled:cursor-wait disabled:opacity-60"
            >
              {videoReady ? "Prendre la photo" : "Camera en cours de demarrage..."}
            </button>
          </div>
        )}

        {step === "scanning" && (
          <div className="relative flex flex-col items-center gap-4 overflow-hidden bg-gradient-to-br from-brand to-brand-light p-16 text-white">
            <div className="pointer-events-none absolute inset-0">
              <div className="absolute left-0 right-0 h-0.5 bg-brand-accent/80 shadow-[0_0_16px_3px_rgba(255,255,255,0.5)] animate-scan-line" />
            </div>
            <div className="glass-pill relative flex h-16 w-16 items-center justify-center">
              <span className="absolute inset-0 rounded-full border-2 border-brand-accent animate-pulse-ring" />
              <SearchIcon className="text-2xl" />
            </div>
            <p className="animate-scan-pulse font-medium tracking-wide">Analyse faciale en cours...</p>
          </div>
        )}

        {step === "error" && (
          <div className="flex flex-col items-center gap-5 bg-gradient-to-br from-brand to-brand-light p-10 text-center text-white">
            <div className="glass-pill flex h-12 w-12 items-center justify-center text-2xl">
              <AlertIcon />
            </div>
            <p>{error}</p>
            <button type="button" onClick={() => setStep("consent")} className="btn-accent">
              Reessayer
            </button>
          </div>
        )}

        {step === "results" && (
          <div className="flex flex-1 flex-col overflow-hidden">
            <div className="flex items-center justify-between border-b border-ink-900/5 px-6 py-4">
              <h2 className="font-semibold">
                {matches.length > 0 ? `${matches.length} photo(s) trouvee(s)` : "Aucune photo trouvee"}
              </h2>
            </div>

            {matches.length === 0 ? (
              <div className="flex flex-1 flex-col items-center justify-center gap-4 p-10 text-center text-ink-500">
                <p>Aucune photo ne correspond a ce visage pour le moment.</p>
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    router.push(`/event/${eventId}/gallery`);
                  }}
                  className="btn-ghost"
                >
                  Parcourir la galerie
                </button>
              </div>
            ) : (
              <div className="grid flex-1 grid-cols-3 gap-2 overflow-y-auto p-4 sm:grid-cols-4">
                {matches.map(({ photo }, i) => {
                  const isSelected = selectedIds.has(photo.id);
                  return (
                    <div key={photo.id} className="group relative aspect-square overflow-hidden rounded-xl bg-surface-alt">
                      <button
                        type="button"
                        onClick={() => setLightboxIndex(i)}
                        className="block h-full w-full"
                      >
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={photo.thumbnail_url}
                          alt={photo.original_filename}
                          className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                        />
                      </button>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (!isSelected) flyToCart(e.currentTarget.closest(".group"));
                          handlePhotoClick(photo);
                        }}
                        className={`glass-pill absolute right-1.5 top-1.5 flex h-7 w-7 items-center justify-center text-xs font-bold shadow transition-all duration-200 active:scale-90 ${
                          isSelected ? "!bg-brand-accent !text-brand" : "text-white"
                        }`}
                      >
                        {isSelected ? <CheckIcon /> : null}
                      </button>
                    </div>
                  );
                })}
              </div>
            )}

            {cartCount > 0 && (
              <div className="border-t border-ink-900/5 p-4">
                <button
                  type="button"
                  disabled={goingToCart}
                  onClick={goToCart}
                  className="btn-primary w-full justify-between px-5 disabled:opacity-70"
                >
                  <span>{cartCount} photo(s) selectionnee(s)</span>
                  <span className="text-brand-accent-light">
                    {goingToCart ? "Enregistrement..." : "Voir le panier →"}
                  </span>
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Clics de la visionneuse arretes ici : sinon fermer une photo
          remontait jusqu'au fond du dialogue et fermait tout le scan (les
          resultats etaient perdus). */}
      {lightboxIndex !== null && (
        <div onClick={(e) => e.stopPropagation()}>
          <PhotoLightbox
            photos={matches.map((m) => m.photo)}
            index={lightboxIndex}
            onClose={() => setLightboxIndex(null)}
            onNavigate={setLightboxIndex}
            selectedPhotoIds={selectedIds}
            onToggleSelect={handlePhotoClick}
          />
        </div>
      )}
    </div>
  );
}
