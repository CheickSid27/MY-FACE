"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import RequireAuth from "@/components/admin/RequireAuth";
import BatchUploader from "@/components/upload/BatchUploader";
import { api } from "@/lib/api-client";
import type { Event, Photo } from "@/types/api";

function AdminEventDetailContent() {
  const { eventId } = useParams<{ eventId: string }>();
  const router = useRouter();
  const [event, setEvent] = useState<Event | null>(null);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [eventData, photosData] = await Promise.all([
        api.getEvent(eventId),
        api.listPhotos(eventId, 1, 100),
      ]);
      setEvent(eventData);
      setPhotos(photosData.items);
      setTotal(photosData.total);
    } catch {
      setError("Impossible de charger l'evenement.");
    }
  }, [eventId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  async function handleDelete() {
    if (!confirm("Supprimer definitivement cet evenement et toutes ses photos ?")) return;
    await api.deleteEvent(eventId);
    router.push("/admin/events");
  }

  if (error) return <p className="p-6 text-red-600">{error}</p>;
  if (!event) return <p className="p-6 text-ink-500">Chargement...</p>;

  const kioskUrl =
    typeof window !== "undefined" ? `${window.location.origin}/event/${event.id}` : `/event/${event.id}`;

  return (
    <main className="min-h-screen bg-gradient-to-b from-surface-alt to-surface p-6">
      <div className="mx-auto max-w-3xl">
        <button
          type="button"
          onClick={() => router.push("/admin/events")}
          className="mb-4 text-sm font-medium text-ink-500 transition hover:text-brand"
        >
          &larr; Retour aux evenements
        </button>

        <div className="glass mb-6 flex items-start justify-between rounded-2xl p-5">
          <div>
            <h1 className="text-xl font-bold text-ink-900">{event.name}</h1>
            <p className="text-sm text-ink-500">
              {new Date(event.date).toLocaleDateString("fr-FR")} &middot; {event.location}
            </p>
            <p className="mt-1 text-sm text-ink-500">
              Prix unitaire : {event.pricing.unit_price} {event.pricing.currency}
            </p>
            <p className="mt-2 text-xs text-ink-300 break-all">Lien borne/QR : {kioskUrl}</p>
          </div>
          <button
            type="button"
            onClick={handleDelete}
            className="text-sm font-medium text-red-600 transition hover:text-red-800"
          >
            Supprimer
          </button>
        </div>

        <div className="mb-6">
          <BatchUploader eventId={eventId} onUploaded={loadData} />
        </div>

        <div className="mb-6 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => router.push(`/admin/events/${eventId}/clusters`)}
            className="btn-primary !px-4 !py-2.5 text-sm"
          >
            Voir les personnes detectees
          </button>
          <button
            type="button"
            onClick={() => router.push(`/admin/events/${eventId}/stats`)}
            className="btn-accent !px-4 !py-2.5 text-sm"
          >
            Statistiques
          </button>
          <button
            type="button"
            onClick={() => router.push(`/admin/events/${eventId}/payments`)}
            className="btn-ghost !px-4 !py-2.5 text-sm"
          >
            Paiements
          </button>
        </div>

        <h2 className="mb-3 text-lg font-semibold text-ink-900">Photos ({total})</h2>
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-6">
          {photos.map((photo) => (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              key={photo.id}
              src={photo.thumbnail_url}
              alt={photo.original_filename}
              className="aspect-square w-full rounded-lg object-cover shadow-soft"
            />
          ))}
        </div>
        {photos.length === 0 && <p className="text-ink-500">Aucune photo uploadee.</p>}
      </div>
    </main>
  );
}

export default function AdminEventDetailPage() {
  return (
    <RequireAuth>
      <AdminEventDetailContent />
    </RequireAuth>
  );
}
