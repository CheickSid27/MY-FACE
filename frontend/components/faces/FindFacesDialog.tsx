"use client";

import { useEffect, useState } from "react";
import PhotoLightbox from "@/components/gallery/PhotoLightbox";
import { UsersIcon } from "@/components/icons";
import { api } from "@/lib/api-client";
import type { FaceCluster, Photo } from "@/types/api";

interface FindFacesDialogProps {
  eventId: string;
  open: boolean;
  onClose: () => void;
  selectedPhotoIds: Set<string>;
  onToggleSelect: (photo: Photo) => void;
  addingPhotoId?: string | null;
}

export default function FindFacesDialog({
  eventId,
  open,
  onClose,
  selectedPhotoIds,
  onToggleSelect,
  addingPhotoId,
}: FindFacesDialogProps) {
  const [clusters, setClusters] = useState<FaceCluster[]>([]);
  const [photosById, setPhotosById] = useState<Record<string, Photo>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCluster, setSelectedCluster] = useState<FaceCluster | null>(null);

  useEffect(() => {
    if (!open) {
      setSelectedCluster(null);
      return;
    }
    setLoading(true);
    setError(null);
    Promise.all([api.getClustersPublic(eventId), api.listPhotos(eventId, 1, 200)])
      .then(([clusterData, photoData]) => {
        setClusters(clusterData.clusters);
        const byId: Record<string, Photo> = {};
        photoData.items.forEach((p) => {
          byId[p.id] = p;
        });
        setPhotosById(byId);
      })
      .catch(() => setError("Impossible de charger les visages detectes."))
      .finally(() => setLoading(false));
  }, [open, eventId]);

  if (!open) return null;

  const clusterPhotos = selectedCluster
    ? selectedCluster.photo_ids.map((id) => photosById[id]).filter((p): p is Photo => Boolean(p))
    : [];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-brand/70 p-4 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="glass-strong relative flex max-h-[92vh] w-full max-w-xl flex-col overflow-hidden rounded-2xl shadow-elevated animate-scale-in"
      >
        <button
          type="button"
          onClick={onClose}
          className="glass-pill absolute right-4 top-4 z-10 flex h-9 w-9 items-center justify-center text-ink-700 transition hover:bg-white/40"
          aria-label="Fermer"
        >
          &times;
        </button>

        <div className="border-b border-ink-900/5 px-6 py-5">
          <h2 className="text-lg font-bold text-ink-900">Trouver mon visage</h2>
          <p className="mt-1 text-sm text-ink-500">
            Voici les visages detectes sur les photos de l&apos;evenement, regroupes par
            ressemblance. Cliquez sur celui qui vous correspond.
          </p>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {loading && (
            <div className="grid grid-cols-3 gap-3 sm:grid-cols-4">
              {Array.from({ length: 9 }).map((_, i) => (
                <div key={i} className="aspect-square animate-pulse rounded-xl bg-surface-alt" />
              ))}
            </div>
          )}
          {error && <p className="text-center text-sm text-red-600">{error}</p>}

          {!loading && !error && clusters.length === 0 && (
            <div className="flex flex-col items-center gap-2 py-10 text-center text-ink-500">
              <UsersIcon className="text-3xl" />
              <p>Aucun visage detecte pour le moment.</p>
            </div>
          )}

          {!loading && !error && clusters.length > 0 && (
            <div className="grid grid-cols-3 gap-3 sm:grid-cols-4">
              {clusters.map((cluster) => (
                <button
                  key={cluster.cluster_id}
                  type="button"
                  onClick={() => setSelectedCluster(cluster)}
                  className="group relative overflow-hidden rounded-xl shadow-soft transition-all duration-200 hover:-translate-y-0.5 hover:shadow-card"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={cluster.representative_photo.thumbnail_url}
                    alt={`Personne ${cluster.cluster_id}`}
                    className="aspect-square w-full object-cover transition-transform duration-300 group-hover:scale-105"
                  />
                  <span className="absolute bottom-1.5 right-1.5 glass-pill px-2 py-0.5 text-[10px] font-semibold text-white">
                    {cluster.photo_count}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {selectedCluster && (
        <ClusterLightbox
          cluster={selectedCluster}
          photos={clusterPhotos}
          onClose={() => setSelectedCluster(null)}
          selectedPhotoIds={selectedPhotoIds}
          onToggleSelect={onToggleSelect}
          addingPhotoId={addingPhotoId}
        />
      )}
    </div>
  );
}

function ClusterLightbox({
  cluster,
  photos,
  onClose,
  selectedPhotoIds,
  onToggleSelect,
  addingPhotoId,
}: {
  cluster: FaceCluster;
  photos: Photo[];
  onClose: () => void;
  selectedPhotoIds: Set<string>;
  onToggleSelect: (photo: Photo) => void;
  addingPhotoId?: string | null;
}) {
  const [index, setIndex] = useState<number | null>(null);

  if (index === null) {
    return (
      <div
        className="fixed inset-0 z-[55] flex items-center justify-center bg-brand/80 p-4 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
      >
        <div
          className="glass-strong max-h-[80vh] w-full max-w-xl overflow-y-auto rounded-2xl p-5 shadow-elevated animate-scale-in"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="mb-4 flex items-center justify-between">
            <h3 className="font-semibold text-ink-900">
              Personne {cluster.cluster_id} &mdash; {cluster.photo_count} photo(s)
            </h3>
            <button
              type="button"
              onClick={onClose}
              className="glass-pill flex h-8 w-8 items-center justify-center text-ink-500 transition hover:text-ink-900"
            >
              &times;
            </button>
          </div>
          <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
            {photos.map((photo, i) => (
              <button
                key={photo.id}
                type="button"
                onClick={() => setIndex(i)}
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
    );
  }

  return (
    <PhotoLightbox
      photos={photos}
      index={index}
      onClose={onClose}
      onNavigate={setIndex}
      selectedPhotoIds={selectedPhotoIds}
      onToggleSelect={onToggleSelect}
      addingPhotoId={addingPhotoId}
    />
  );
}
