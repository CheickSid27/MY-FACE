"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { CheckIcon, PrinterIcon } from "@/components/icons";
import { api, ApiError } from "@/lib/api-client";
import { clearCartSessionId } from "@/lib/cart";
import { isKioskMode } from "@/lib/kiosk";
import type { DownloadResponse } from "@/types/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const INACTIVITY_TIMEOUT_MS = 90_000;

export default function DownloadPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const router = useRouter();
  const [data, setData] = useState<DownloadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api
      .getDownload(orderId)
      .then((result) => {
        setData(result);
        // La commande est terminee : on vide le panier de cet evenement pour
        // que le client (ou le suivant sur la meme borne) reparte d'un
        // panier vide au lieu de retrouver les articles deja payes.
        clearCartSessionId(result.event_id);
      })
      .catch((err) =>
        setError(
          err instanceof ApiError
            ? err.message
            : "Impossible de charger les liens de téléchargement."
        )
      );
  }, [orderId]);

  useEffect(() => {
    load();
  }, [load]);

  // Les liens signes expirent (voir expires_in) mais l'acces a la commande,
  // lui, est permanent : si la page reste ouverte, on les renouvelle un peu
  // avant leur expiration pour que "Telecharger" marche toujours.
  useEffect(() => {
    if (!data) return;
    const refreshMs = Math.max(60, data.expires_in - 120) * 1000;
    const timer = setTimeout(load, refreshMs);
    return () => clearTimeout(timer);
  }, [data, load]);

  const kiosk = data != null && isKioskMode(data.event_id);
  const printPhotos = data?.photos.filter((p) => p.print_requested) ?? [];
  const showPrintButton = printPhotos.length > 0 && kiosk;

  // Retour automatique a la galerie si le client reste inactif : evite
  // qu'une borne partagee reste bloquee sur la page de telechargement d'un
  // client precedent. Borne uniquement : sur son propre telephone, le client
  // doit pouvoir prendre son temps.
  const inactivityTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const goToGallery = useCallback(() => {
    if (data) router.push(`/event/${data.event_id}/gallery`);
  }, [data, router]);

  useEffect(() => {
    if (!data || !kiosk) return;

    function resetTimer() {
      if (inactivityTimerRef.current) clearTimeout(inactivityTimerRef.current);
      inactivityTimerRef.current = setTimeout(goToGallery, INACTIVITY_TIMEOUT_MS);
    }

    const events = ["pointerdown", "keydown", "scroll", "touchstart"];
    events.forEach((evt) => window.addEventListener(evt, resetTimer));
    resetTimer();

    return () => {
      events.forEach((evt) => window.removeEventListener(evt, resetTimer));
      if (inactivityTimerRef.current) clearTimeout(inactivityTimerRef.current);
    };
  }, [data, kiosk, goToGallery]);

  if (error) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand to-brand-light px-6 text-center text-white">
        <p className="text-lg">{error}</p>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand to-brand-light text-white">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-accent border-t-transparent" />
      </main>
    );
  }

  return (
    <main className="flex min-h-screen flex-col items-center gap-8 bg-gradient-to-b from-surface-alt to-surface px-6 py-12 animate-fade-in">
      <div className="text-center">
        <div className="glass-pill mx-auto mb-4 flex h-16 w-16 items-center justify-center text-3xl !bg-emerald-500/15 text-emerald-600">
          <CheckIcon />
        </div>
        <h1 className="text-2xl font-bold text-brand">Paiement confirmé !</h1>
        <p className="mx-auto mt-1 max-w-md text-ink-500">
          {data.photos.length > 1 ? `Vos ${data.photos.length} photos` : "Votre photo"} en qualité originale{" "}
          {data.photos.length > 1 ? "sont prêtes" : "est prête"}. Elles restent
          disponibles à tout moment depuis ce lien ou le QR code ci-dessous.
        </p>
      </div>

      <a
        href={`${API_URL}/download/${orderId}/zip`}
        className="btn-accent w-full max-w-sm !py-4 text-center text-base"
      >
        Télécharger toutes mes photos ({data.photos.length})
      </a>

      {/* Impression papier : uniquement sur la borne (imprimante physique
          branchée a côté), jamais propose sur le téléphone d'un invité. */}
      {showPrintButton && (
        <button
          type="button"
          onClick={() => router.push(`/order/${orderId}/print`)}
          className="btn-primary flex w-full max-w-sm items-center justify-center gap-2 !py-4 text-base"
        >
          <PrinterIcon /> Imprimer mes photos ({printPhotos.length})
        </button>
      )}

      <div className="glass flex flex-col items-center gap-3 rounded-2xl p-5">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={`${API_URL}/download/${orderId}/qr.png`}
          alt="QR code de téléchargement"
          className="h-40 w-40 rounded-lg"
        />
        <p className="max-w-[220px] text-center text-xs text-ink-500">
          Scannez ce QR code pour retrouver vos photos sur un autre appareil, maintenant ou plus
          tard.
        </p>
      </div>

      <div className="grid w-full max-w-2xl grid-cols-2 gap-3 sm:grid-cols-4">
        {data.photos.map((photo) => (
          <div key={photo.photo_id} className="glass flex flex-col overflow-hidden rounded-xl">
            {/* Miniature pour l'apercu : afficher les originaux ici faisait
                télécharger plusieurs Mo par photo rien que pour voir la liste. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={photo.thumbnail_url}
              alt={photo.filename}
              loading="lazy"
              className="aspect-square w-full object-cover"
            />
            <a
              href={photo.url}
              download={photo.filename}
              className="flex items-center justify-center gap-1 px-2 py-2 text-xs font-semibold text-brand transition hover:bg-white/60"
            >
              <span aria-hidden>&darr;</span> Télécharger
            </a>
          </div>
        ))}
      </div>

      <button type="button" onClick={goToGallery} className="btn-ghost w-full max-w-sm">
        Retour à la galerie
      </button>
    </main>
  );
}
