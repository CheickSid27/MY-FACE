"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { CheckIcon } from "@/components/icons";
import { api, ApiError } from "@/lib/api-client";
import type { DownloadResponse } from "@/types/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const INACTIVITY_TIMEOUT_MS = 90_000;

export default function DownloadPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const router = useRouter();
  const [data, setData] = useState<DownloadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getDownload(orderId)
      .then(setData)
      .catch((err) =>
        setError(
          err instanceof ApiError
            ? err.message
            : "Impossible de charger les liens de telechargement."
        )
      );
  }, [orderId]);

  // Retour automatique a la galerie si le client reste inactif : evite
  // qu'une borne/tablette partagee reste bloquee sur la page de telechargement
  // d'un client precedent.
  const inactivityTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const goToGallery = useCallback(() => {
    if (data) router.push(`/event/${data.event_id}/gallery`);
  }, [data, router]);

  useEffect(() => {
    if (!data) return;

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
  }, [data, goToGallery]);

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
        <h1 className="text-2xl font-bold text-brand">Paiement confirme !</h1>
        <p className="mt-1 text-ink-500">
          Vos {data.photos.length} photo(s) sont pretes. Les liens expirent dans{" "}
          {Math.round(data.expires_in / 60)} minutes.
        </p>
      </div>

      <a
        href={`${API_URL}/download/${orderId}/zip`}
        className="btn-accent w-full max-w-sm !py-4 text-center text-base"
      >
        Telecharger toutes mes photos ({data.photos.length})
      </a>

      <div className="glass flex flex-col items-center gap-3 rounded-2xl p-5">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={`${API_URL}/download/${orderId}/qr.png`}
          alt="QR code de telechargement"
          className="h-40 w-40 rounded-lg"
        />
        <p className="max-w-[200px] text-center text-xs text-ink-500">
          Scannez ce QR code pour retrouver ce lien sur un autre appareil.
        </p>
      </div>

      <div className="grid w-full max-w-2xl grid-cols-3 gap-3 sm:grid-cols-4">
        {data.photos.map((photo) => (
          <div key={photo.photo_id} className="glass overflow-hidden rounded-xl">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={photo.url}
              alt={photo.filename}
              className="aspect-square w-full object-cover"
            />
          </div>
        ))}
      </div>

      <button type="button" onClick={goToGallery} className="btn-ghost w-full max-w-sm">
        Retour a la galerie
      </button>
    </main>
  );
}
