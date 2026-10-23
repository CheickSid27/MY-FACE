"use client";

import { useEffect, useState } from "react";
import PhotoLightbox from "@/components/gallery/PhotoLightbox";
import { UsersIcon } from "@/components/icons";
import { api, ApiError } from "@/lib/api-client";
import { bulkDeleteMessage } from "@/lib/bulk-delete";
import type { FaceCluster } from "@/types/api";

/** Volet « Visages » d'un evenement : groupes de visages detectes par l'IA
 * (pre-groupage, pas des identites verifiees). */
export default function EventFacesPanel({ eventId, onPhotosDeleted }: { eventId: string; onPhotosDeleted?: () => void }) {
  const [clusters, setClusters] = useState<FaceCluster[]>([]);
  const [unclusteredCount, setUnclusteredCount] = useState(0);
  const [selectedCluster, setSelectedCluster] = useState<FaceCluster | null>(null);
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  // Une personne demande le retrait de ses photos : toutes les photos de son
  // groupe sont supprimees d'un coup (sauf celles deja vendues).
  async function deletePersonPhotos(cluster: FaceCluster) {
    const n = cluster.photos.length;
    if (!confirm(`Supprimer définitivement les ${n} photo${n > 1 ? "s" : ""} de cette personne ? Les invités ne les verront plus.`)) return;
    setDeleting(true);
    try {
      const result = await api.bulkDeletePhotos(eventId, cluster.photos.map((p) => p.id));
      setNotice(bulkDeleteMessage(result));
      setSelectedCluster(null);
      const fresh = await api.getClusters(eventId);
      setClusters(fresh.clusters);
      setUnclusteredCount(fresh.unclustered_count);
      onPhotosDeleted?.();
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Suppression impossible, réessayez.");
    } finally {
      setDeleting(false);
    }
  }

  useEffect(() => {
    api
      .getClusters(eventId)
      .then((clusterData) => {
        setClusters(clusterData.clusters);
        setUnclusteredCount(clusterData.unclustered_count);
      })
      .catch(() => setError("Impossible de charger les personnes détectées."))
      .finally(() => setLoading(false));
  }, [eventId]);

  // Chaque cluster embarque deja ses photos completes (voir backend
  // schemas/face.py) : plus besoin de recouper avec une liste paginee a
  // part, qui tronquait silencieusement les clusters au-dela des 200
  // premieres photos de l'evenement.
  const clusterPhotos = selectedCluster?.photos ?? [];
  const noopSelect = () => {};

  return (
    <div>
        <p className="mb-4 text-sm text-ink-500">
          Les visages sont regroupés automatiquement par ressemblance. Touchez un groupe pour voir ses photos, ou les
          supprimer toutes si la personne le demande.
        </p>
        {notice && <p className="mb-4 rounded-2xl bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</p>}

        {loading && (
          <div className="grid grid-cols-3 gap-4 sm:grid-cols-4 md:grid-cols-6">
            {Array.from({ length: 12 }).map((_, i) => (
              <div key={i} className="aspect-square animate-pulse rounded-xl bg-surface-alt" />
            ))}
          </div>
        )}
        {error && <p className="text-red-600">{error}</p>}

        {!loading && !error && (
          <>
            <div className="grid grid-cols-3 gap-4 sm:grid-cols-4 md:grid-cols-6">
              {clusters.map((cluster, i) => (
                <button
                  key={cluster.cluster_id}
                  type="button"
                  onClick={() => setSelectedCluster(cluster)}
                  className="card group overflow-hidden p-2 text-left transition-all duration-200 hover:-translate-y-0.5 hover:shadow-card"
                >
                  <div className="relative overflow-hidden rounded-lg">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={cluster.representative_face_url}
                      alt={`Personne ${i + 1}`}
                      className="aspect-square w-full object-cover transition-transform duration-300 group-hover:scale-105"
                    />
                    <span className="absolute bottom-1.5 right-1.5 rounded-full bg-black/60 px-2 py-0.5 text-[10px] font-semibold text-white backdrop-blur">
                      {cluster.photo_count}
                    </span>
                  </div>
                </button>
              ))}
            </div>

            {clusters.length === 0 && (
              <div className="card flex flex-col items-center gap-2 p-10 text-center text-ink-500">
                <UsersIcon className="text-3xl" />
                <p>
                  Aucun groupe détecté pour le moment (indexation en cours ou pas assez de visages
                  similaires).
                </p>
              </div>
            )}

            {unclusteredCount > 0 && (
              <p className="mt-6 text-sm text-ink-500">
                {unclusteredCount} visage(s) non groupe(s) (trop peu de photos similaires pour
                former un groupe).
              </p>
            )}
          </>
        )}

        {selectedCluster && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-brand/70 p-4 backdrop-blur-sm animate-fade-in"
            onClick={() => setSelectedCluster(null)}
          >
            <div
              className="glass-strong max-h-[80vh] w-full max-w-2xl overflow-y-auto rounded-2xl p-5 shadow-elevated animate-scale-in"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="mb-4 flex items-center justify-between">
                <h2 className="font-semibold text-ink-900">
                  Personne {clusters.indexOf(selectedCluster) + 1}, {selectedCluster.photo_count} photo{selectedCluster.photo_count > 1 ? "s" : ""}
                </h2>
                <button
                  type="button"
                  onClick={() => setSelectedCluster(null)}
                  className="glass-pill flex h-8 w-8 items-center justify-center text-ink-500 transition hover:text-ink-900"
                >
                  &times;
                </button>
              </div>
              <button
                type="button"
                onClick={() => deletePersonPhotos(selectedCluster)}
                disabled={deleting}
                className="mb-4 flex min-h-[44px] w-full items-center justify-center rounded-xl border border-red-200 bg-white text-sm font-semibold text-red-700 transition hover:bg-red-50 disabled:opacity-60"
              >
                {deleting ? "Suppression..." : `Supprimer toutes ses photos (${selectedCluster.photos.length})`}
              </button>
              <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
                {clusterPhotos.map((photo, i) => (
                  <button
                    key={photo.id}
                    type="button"
                    onClick={() => setLightboxIndex(i)}
                    className="group aspect-square overflow-hidden rounded-lg"
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={photo.thumbnail_url}
                      alt={photo.original_filename}
                      className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                    />
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {lightboxIndex !== null && (
          <PhotoLightbox
            photos={clusterPhotos}
            index={lightboxIndex}
            onClose={() => setLightboxIndex(null)}
            onNavigate={setLightboxIndex}
            selectedPhotoIds={new Set()}
            onToggleSelect={noopSelect}
            showCartAction={false}
            showFileName
          />
        )}
    </div>
  );
}
