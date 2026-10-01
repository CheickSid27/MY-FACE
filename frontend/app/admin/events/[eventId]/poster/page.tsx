"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import RequireAuth from "@/components/admin/RequireAuth";
import MyfaceLogo from "@/components/brand/Logo";
import { PrinterIcon } from "@/components/icons";
import { api } from "@/lib/api-client";
import type { Event } from "@/types/api";

// Affiche A4 a imprimer et poser sur place (entree, tables, borne) : le QR
// du lien invite, en grand, avec le mode d'emploi en trois etapes.
function PosterContent() {
  const { eventId } = useParams<{ eventId: string }>();
  const router = useRouter();
  const [event, setEvent] = useState<Event | null>(null);
  const [qrUrl, setQrUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let created: string | null = null;
    Promise.all([api.getEvent(eventId), api.getEventQrObjectUrl(eventId, "guest")])
      .then(([eventData, url]) => {
        created = url;
        setEvent(eventData);
        setQrUrl(url);
      })
      .catch(() => setError("Impossible de preparer l'affiche."));
    return () => {
      if (created) URL.revokeObjectURL(created);
    };
  }, [eventId]);

  if (error) return <p className="p-6 text-red-600">{error}</p>;
  if (!event || !qrUrl) return <p className="p-6 text-ink-500">Chargement...</p>;

  return (
    <>
      <style>{`
        @page { size: A4 portrait; margin: 12mm; }
        @media print { html, body { background: #fff !important; } }
      `}</style>

      <div className="flex items-center justify-between gap-3 p-4 print:hidden">
        <button
          type="button"
          onClick={() => router.push(`/admin/events/${eventId}`)}
          className="text-sm font-medium text-ink-500 transition hover:text-brand"
        >
          &larr; Retour a l&apos;evenement
        </button>
        <button type="button" onClick={() => window.print()} className="btn-accent flex items-center gap-2 !px-5 !py-2.5 text-sm">
          <PrinterIcon /> Imprimer
        </button>
      </div>

      <main className="mx-auto flex max-w-[190mm] flex-col items-center gap-8 bg-white px-8 py-10 text-center text-ink-900 shadow-card print:shadow-none">
        <MyfaceLogo size={62} />

        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-brand-accent">Vos photos</p>
          <h1 className="mt-3 font-display text-4xl font-semibold uppercase tracking-wide">
            {event.frame_caption || event.name}
          </h1>
          <p className="mt-2 text-ink-500">
            {new Date(event.date).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" })}{" "}
            &middot; {event.location}
          </p>
        </div>

        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={qrUrl} alt="QR code pour retrouver vos photos" className="h-[95mm] w-[95mm]" />

        <ol className="grid w-full max-w-lg gap-4 text-left sm:grid-cols-3">
          {[
            ["Scannez", "ce QR code avec l'appareil photo de votre telephone"],
            ["Prenez un selfie", "pour retrouver toutes les photos ou vous apparaissez"],
            ["Achetez", "et telechargez-les en qualite originale"],
          ].map(([title, text], i) => (
            <li key={title} className="flex flex-col items-center text-center">
              <span className="mb-2 flex h-9 w-9 items-center justify-center rounded-full bg-brand text-sm font-bold text-white">
                {i + 1}
              </span>
              <p className="font-semibold">{title}</p>
              <p className="text-xs text-ink-500">{text}</p>
            </li>
          ))}
        </ol>

        <p className="break-all text-xs text-ink-500">{event.guest_url}</p>

        <div className="flex items-center gap-2 border-t border-ink-900/10 pt-5">
          <MyfaceLogo size={24} />
          <span className="text-sm font-bold text-ink-900">
            MY<span className="text-[#F26A1B]">FACE</span>
          </span>
          <span className="text-sm text-ink-500">&middot; Scanne. Retrouve. Repars avec.</span>
        </div>
      </main>
    </>
  );
}

export default function PosterPage() {
  return (
    <RequireAuth>
      <PosterContent />
    </RequireAuth>
  );
}
