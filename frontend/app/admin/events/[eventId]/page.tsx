"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import RequireAuth from "@/components/admin/RequireAuth";
import BatchUploader from "@/components/upload/BatchUploader";
import { CrossIcon } from "@/components/icons";
import { api, ApiError } from "@/lib/api-client";
import type { Event, Photo, WatchedFolderRead } from "@/types/api";

const WATCHED_FOLDER_POLL_MS = 5000;

function AdminEventDetailContent() {
  const { eventId } = useParams<{ eventId: string }>();
  const router = useRouter();
  const [event, setEvent] = useState<Event | null>(null);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [watchedFolder, setWatchedFolder] = useState<WatchedFolderRead | null>(null);

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

  // Etat du dossier surveille : rafraichi periodiquement pour que l'admin
  // voie en direct les photos deposees depuis la carte SD de l'appareil se
  // faire ingerer, sans avoir a recharger la page.
  useEffect(() => {
    let cancelled = false;
    function poll() {
      api
        .getWatchedFolder(eventId)
        .then((data) => {
          if (!cancelled) setWatchedFolder(data);
        })
        .catch(() => {
          // dossier surveille indisponible (ex: pas encore configure) : silencieux
        });
    }
    poll();
    const interval = setInterval(poll, WATCHED_FOLDER_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [eventId]);

  async function handleDelete() {
    if (!confirm("Supprimer definitivement cet evenement et toutes ses photos ?")) return;
    await api.deleteEvent(eventId);
    router.push("/admin/events");
  }

  const [deletingPhotoId, setDeletingPhotoId] = useState<string | null>(null);

  async function handleDeletePhoto(photo: Photo) {
    if (!confirm(`Supprimer definitivement "${photo.original_filename}" ?`)) return;
    setDeletingPhotoId(photo.id);
    try {
      await api.deletePhoto(photo.id);
      setPhotos((prev) => prev.filter((p) => p.id !== photo.id));
      setTotal((t) => t - 1);
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Impossible de supprimer cette photo.");
    } finally {
      setDeletingPhotoId(null);
    }
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

        {watchedFolder && (
          <div className="glass mb-6 rounded-2xl p-5">
            <h2 className="mb-1 text-sm font-semibold text-ink-900">Dossier surveille</h2>
            <p className="mb-3 text-xs text-ink-500">
              Deposez les photos (ex: depuis la carte SD de l&apos;appareil) dans ce dossier sur le
              PC : elles sont ajoutees automatiquement, sans passer par l&apos;upload manuel.
            </p>
            <code className="mb-3 block break-all rounded-lg bg-surface-alt px-3 py-2 text-xs text-ink-900">
              {watchedFolder.folder_path}
            </code>
            {watchedFolder.files.length > 0 && (
              <ul className="flex flex-col gap-1.5">
                {watchedFolder.files.map((f) => (
                  <li key={f.filename} className="flex items-center justify-between gap-3 text-xs">
                    <span className="truncate text-ink-700">{f.filename}</span>
                    <span
                      className={`shrink-0 rounded-full px-2 py-0.5 font-medium ${
                        f.status === "ingested"
                          ? "bg-emerald-100 text-emerald-700"
                          : f.status === "error"
                            ? "bg-red-100 text-red-700"
                            : "bg-amber-100 text-amber-700"
                      }`}
                    >
                      {f.status === "ingested"
                        ? "Ajoutee"
                        : f.status === "error"
                          ? `Erreur${f.detail ? ` : ${f.detail}` : ""}`
                          : "Copie en cours..."}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

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
            <div key={photo.id} className="group relative overflow-hidden rounded-lg shadow-soft">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={photo.thumbnail_url}
                alt={photo.original_filename}
                className="aspect-square w-full object-cover"
              />
              <button
                type="button"
                onClick={() => handleDeletePhoto(photo)}
                disabled={deletingPhotoId === photo.id}
                aria-label={`Supprimer ${photo.original_filename}`}
                className="absolute right-1 top-1 flex h-6 w-6 items-center justify-center rounded-full bg-black/60 text-xs text-white transition-colors duration-150 hover:bg-red-600 disabled:cursor-wait"
              >
                <CrossIcon />
              </button>
            </div>
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
