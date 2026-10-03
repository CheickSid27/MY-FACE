"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import MyfaceLogo from "@/components/brand/Logo";
import FramedPhoto from "@/components/photo/FramedPhoto";
import ScanDialog from "@/components/scan/ScanDialog";
import { api } from "@/lib/api-client";
import { forgetKioskToken, getKioskToken, rememberKioskToken } from "@/lib/kiosk";
import type { EventPublicRead, Photo } from "@/types/api";

export default function EventHomePage() {
  const { eventId } = useParams<{ eventId: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [event, setEvent] = useState<EventPublicRead | null>(null);
  const [featuredPhoto, setFeaturedPhoto] = useState<Photo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [scanOpen, setScanOpen] = useState(false);

  // Detection du mode borne : le lien configure sur la borne physique porte
  // ?kiosk=<le vrai kiosk_token de l'evenement> (voir admin, page evenement).
  // Sans ce parametre (retour a l'accueil, reset d'inactivite...), on
  // re-verifie le jeton deja memorise pour cette session. Le serveur seul
  // decide si le jeton est valide (is_kiosk) ; voir lib/kiosk.ts.
  const urlKioskToken = searchParams.get("kiosk");
  useEffect(() => {
    const candidate = urlKioskToken ?? getKioskToken(eventId);
    api
      .getEventPublic(eventId, candidate)
      .then((data) => {
        setEvent(data);
        if (data.is_kiosk && candidate) {
          rememberKioskToken(eventId, candidate);
          if (urlKioskToken) {
            // Jeton retire de la barre d'adresse une fois memorise : il n'a
            // pas a rester visible (ni partageable) sur l'ecran de la borne.
            router.replace(`/event/${eventId}`);
          }
        } else if (candidate) {
          // Jeton refuse (lien errone, ou jeton d'un autre evenement) :
          // comportement invite normal.
          forgetKioskToken(eventId);
        }
      })
      .catch(() => setError("Événement introuvable."))
      .finally(() => setLoading(false));
  }, [eventId, urlKioskToken, router]);

  // Photo vedette pour le cadre decoratif de l'accueil (voir
  // Event.frame_caption) : la plus recemment uploadee, pas de selection
  // manuelle d'une "photo de couverture" pour l'instant.
  useEffect(() => {
    if (!event?.frame_caption) return;
    api
      .listPhotos(eventId, 1, 1, event.is_kiosk ? getKioskToken(eventId) : null)
      .then((data) => setFeaturedPhoto(data.items[0] ?? null))
      .catch(() => {
        // pas de photo vedette disponible : le cadre ne s'affiche simplement pas
      });
  }, [eventId, event?.frame_caption, event?.is_kiosk]);

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
        <p className="text-lg">{error || "Événement introuvable."}</p>
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

      {event.frame_caption && featuredPhoto && (
        <div className="relative z-10 mb-8 animate-fade-in">
          <FramedPhoto caption={event.frame_caption}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={featuredPhoto.preview_url}
              alt={event.frame_caption}
              className="h-[42vh] max-h-96 w-auto object-cover sm:h-[48vh]"
            />
          </FramedPhoto>
        </div>
      )}

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

      <div className="relative z-10 mt-14 flex items-center gap-2 opacity-60">
        <MyfaceLogo size={22} tone="light" />
        <span className="text-xs font-semibold tracking-wide text-white">
          MY<span className="text-[#F26A1B]">FACE</span>
        </span>
      </div>

      <ScanDialog eventId={eventId} open={scanOpen} onClose={() => setScanOpen(false)} />
    </main>
  );
}
