"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { CheckIcon, ImageIcon } from "@/components/icons";
import { api, ApiError } from "@/lib/api-client";
import type { DownloadResponse } from "@/types/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function DownloadPage() {
  const { orderId } = useParams<{ orderId: string }>();
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

      <div className="grid w-full max-w-2xl grid-cols-2 gap-4 sm:grid-cols-3">
        {data.photos.map((photo) => (
          <a
            key={photo.photo_id}
            href={photo.url}
            target="_blank"
            rel="noreferrer"
            className="glass group flex flex-col items-center gap-2 rounded-2xl p-4 text-center transition-all duration-200 hover:-translate-y-0.5 hover:shadow-card"
          >
            <ImageIcon className="text-3xl text-ink-500 transition-transform duration-200 group-hover:scale-110" />
            <span className="w-full truncate text-xs text-ink-500">{photo.filename}</span>
            <span className="text-xs font-semibold text-brand">Telecharger</span>
          </a>
        ))}
      </div>
    </main>
  );
}
