"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import RequireAuth from "@/components/admin/RequireAuth";
import PhotoLightbox from "@/components/gallery/PhotoLightbox";
import { UsersIcon } from "@/components/icons";
import { api } from "@/lib/api-client";
import type { FaceCluster, Photo } from "@/types/api";

function ClustersContent() {
  const { eventId } = useParams<{ eventId: string }>();
  const router = useRouter();
  const [clusters, setClusters] = useState<FaceCluster[]>([]);
  const [unclusteredCount, setUnclusteredCount] = useState(0);
  const [photosById, setPhotosById] = useState<Record<string, Photo>>({});
  const [selectedCluster, setSelectedCluster] = useState<FaceCluster | null>(null);
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.getClusters(eventId), api.listPhotos(eventId, 1, 200)])
      .then(([clusterData, photoData]) => {
        setClusters(clusterData.clusters);
        setUnclusteredCount(clusterData.unclustered_count);
        const byId: Record<string, Photo> = {};
        photoData.items.forEach((p) => {
          byId[p.id] = p;
        });
        setPhotosById(byId);
      })
      .catch(() => setError("Impossible de charger les personnes detectees."))
      .finally(() => setLoading(false));
  }, [eventId]);

  const clusterPhotos = selectedCluster
    ? selectedCluster.photo_ids.map((id) => photosById[id]).filter((p): p is Photo => Boolean(p))
    : [];
  const noopSelect = () => {};

  return (
    <main className="min-h-screen bg-gradient-to-b from-surface-alt to-surface p-6">
      <div className="mx-auto max-w-4xl">
        <div className="glass mb-6 flex items-center justify-between rounded-2xl px-4 py-3">
          <button
            type="button"
            onClick={() => router.push(`/admin/events/${eventId}`)}
            className="text-sm font-medium text-ink-500 transition hover:text-brand"
          >
            &larr; Retour a l&apos;evenement
          </button>
        </div>

        <h1 className="mb-1 text-xl font-bold text-ink-900">Personnes detectees</h1>
        <p className="mb-6 text-sm text-ink-500">
          Pre-groupage automatique par similarite de visage (DBSCAN). Ce ne sont pas des
          identites verifiees.
        </p>

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
              {clusters.map((cluster) => (
                <button
                  key={cluster.cluster_id}
                  type="button"
                  onClick={() => setSelectedCluster(cluster)}
                  className="card group overflow-hidden p-2 text-left transition-all duration-200 hover:-translate-y-0.5 hover:shadow-card"
                >
                  <div className="relative overflow-hidden rounded-lg">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={cluster.representative_photo.thumbnail_url}
                      alt={`Personne ${cluster.cluster_id}`}
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
                  Aucun groupe detecte pour le moment (indexation en cours ou pas assez de visages
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
                  Personne {selectedCluster.cluster_id} &mdash; {selectedCluster.photo_count} photo(s)
                </h2>
                <button
                  type="button"
                  onClick={() => setSelectedCluster(null)}
                  className="glass-pill flex h-8 w-8 items-center justify-center text-ink-500 transition hover:text-ink-900"
                >
                  &times;
                </button>
              </div>
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
          />
        )}
      </div>
    </main>
  );
}

export default function ClustersPage() {
  return (
    <RequireAuth>
      <ClustersContent />
    </RequireAuth>
  );
}
