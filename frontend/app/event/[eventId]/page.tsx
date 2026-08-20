"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import ScanDialog from "@/components/scan/ScanDialog";
import { api } from "@/lib/api-client";
import type { EventPublicRead } from "@/types/api";

export default function EventHomePage() {
  const { eventId } = useParams<{ eventId: string }>();
  const router = useRouter();
  const [event, setEvent] = useState<EventPublicRead | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [scanOpen, setScanOpen] = useState(false);

  useEffect(() => {
    api
      .getEventPublic(eventId)
      .then(setEvent)
      .catch(() => setError("Evenement introuvable."))
      .finally(() => setLoading(false));
  }, [eventId]);

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-brand text-white">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-accent border-t-transparent" />
      </main>
    );
  }

  if (error || !event) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-brand px-6 text-center text-white">
        <p className="text-lg">{error || "Evenement introuvable."}</p>
      </main>
    );
  }

  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-brand px-6 text-center text-white">
      <div
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          background:
            "radial-gradient(circle at 20% 20%, rgba(201,161,90,0.25), transparent 45%), radial-gradient(circle at 80% 70%, rgba(201,161,90,0.15), transparent 40%)",
        }}
      />

      <div className="relative z-10 animate-fade-in">
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.3em] text-brand-accent">
          Bienvenue
        </p>
        <h1 className="text-4xl font-bold tracking-tight sm:text-6xl">{event.name}</h1>
        <p className="mt-4 text-lg text-ink-300 sm:text-xl">
          {new Date(event.date).toLocaleDateString("fr-FR", {
            day: "numeric",
            month: "long",
            year: "numeric",
          })}{" "}
          &middot; {event.location}
        </p>
      </div>

      <div className="relative z-10 mt-12 flex w-full max-w-md flex-col gap-4 sm:flex-row">
        <button
          type="button"
          onClick={() => router.push(`/event/${eventId}/gallery`)}
          className="btn-accent flex-1 !py-5 text-lg"
        >
          Parcourir la galerie
        </button>
        <button
          type="button"
          onClick={() => setScanOpen(true)}
          className="btn-ghost flex-1 !border-white/20 !bg-white/5 !py-5 text-lg !text-white hover:!bg-white/10"
        >
          Scanner mon visage
        </button>
      </div>

      <ScanDialog eventId={eventId} open={scanOpen} onClose={() => setScanOpen(false)} />
    </main>
  );
}
