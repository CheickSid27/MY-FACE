"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import PhotoLightbox from "@/components/gallery/PhotoLightbox";
import { AlertIcon, CameraIcon, CheckIcon, SearchIcon } from "@/components/icons";
import { api, ApiError } from "@/lib/api-client";
import { getCartSessionId, setCartSessionId } from "@/lib/cart";
import { flyToCart } from "@/lib/fly-to-cart";
import type { FaceScanMatch, Photo } from "@/types/api";

type Step = "consent" | "camera" | "scanning" | "results" | "error";

interface ScanDialogProps {
  eventId: string;
  open: boolean;
  onClose: () => void;
}

export default function ScanDialog({ eventId, open, onClose }: ScanDialogProps) {
  const router = useRouter();

  const [step, setStep] = useState<Step>("consent");
  const [error, setError] = useState<string | null>(null);
  const [matches, setMatches] = useState<FaceScanMatch[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [cartCount, setCartCount] = useState(0);
  const [addingPhotoId, setAddingPhotoId] = useState<string | null>(null);
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

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

  useEffect(() => {
    if (!open) return;
    const sessionId = getCartSessionId(eventId);
    if (!sessionId) return;
    api
      .getCart(sessionId)
      .then((cart) => {
        setSelectedIds(new Set(cart.items.map((item) => item.photo.id)));
        setCartCount(cart.items.length);
      })
      .catch(() => {
        // panier expire ou introuvable
      });
  }, [open, eventId]);

  async function startCamera() {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } });
      streamRef.current = stream;
      setStep("camera");
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
    } catch {
      setError("Impossible d'acceder a la camera. Verifiez les autorisations de votre navigateur.");
      setStep("error");
    }
  }

  async function capture() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    const blob: Blob | null = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.9));
    if (!blob) return;

    stopCamera();
    setStep("scanning");

    try {
      const result = await api.scanFace(eventId, blob, true);
      setMatches(result.matches);
      setStep("results");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors du scan.");
      setStep("error");
    }
  }

  async function handlePhotoClick(photo: Photo) {
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
              Pour retrouver vos photos, nous analysons temporairement votre visage sur cet
              appareil et le comparons aux photos de l&apos;evenement. Aucune image de votre
              selfie n&apos;est conservee au-dela de cette recherche.
            </p>
            <p className="text-sm leading-relaxed text-ink-300">
              Vous pouvez a tout moment demander la suppression des donnees biometriques
              associees. Cette fonctionnalite est optionnelle.
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
            <div className="glass-dark w-full overflow-hidden rounded-xl p-1.5">
              <video
                ref={videoRef}
                playsInline
                muted
                className="max-h-[60vh] w-full rounded-lg object-cover"
              />
            </div>
            <canvas ref={canvasRef} className="hidden" />
            <button type="button" onClick={capture} className="btn-accent w-full max-w-xs">
              Prendre la photo
            </button>
          </div>
        )}

        {step === "scanning" && (
          <div className="flex flex-col items-center gap-4 bg-gradient-to-br from-brand to-brand-light p-16 text-white">
            <div className="glass-pill relative flex h-16 w-16 items-center justify-center">
              <span className="absolute inset-0 rounded-full border-2 border-brand-accent animate-pulse-ring" />
              <SearchIcon className="text-2xl" />
            </div>
            <p className="font-medium">Recherche de vos photos...</p>
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
                  const isAdding = addingPhotoId === photo.id;
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
                        disabled={isAdding}
                        onClick={(e) => {
                          e.stopPropagation();
                          if (!isSelected) flyToCart(e.currentTarget.closest(".group"));
                          handlePhotoClick(photo);
                        }}
                        className={`glass-pill absolute right-1.5 top-1.5 flex h-7 w-7 items-center justify-center text-xs font-bold shadow transition-all duration-200 active:scale-90 disabled:opacity-60 ${
                          isSelected ? "!bg-brand-accent !text-brand" : "text-white"
                        }`}
                      >
                        {isAdding ? (
                          <span className="h-2.5 w-2.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
                        ) : isSelected ? (
                          <CheckIcon />
                        ) : null}
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
                  onClick={() => {
                    onClose();
                    router.push(`/event/${eventId}/cart`);
                  }}
                  className="btn-primary w-full justify-between px-5"
                >
                  <span>{cartCount} photo(s) selectionnee(s)</span>
                  <span className="text-brand-accent-light">Voir le panier &rarr;</span>
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {lightboxIndex !== null && (
        <PhotoLightbox
          photos={matches.map((m) => m.photo)}
          index={lightboxIndex}
          onClose={() => setLightboxIndex(null)}
          onNavigate={setLightboxIndex}
          selectedPhotoIds={selectedIds}
          onToggleSelect={handlePhotoClick}
          addingPhotoId={addingPhotoId}
        />
      )}
    </div>
  );
}
